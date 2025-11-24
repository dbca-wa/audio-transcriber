import argparse
import logging
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

import whisper
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobClient, ContainerClient
from dotenv import load_dotenv
from whisper.utils import get_writer

# Load environment variables.
load_dotenv()
# Assumes a connection string secret present as an environment variable.
CONN_STR = os.getenv("AZURE_CONNECTION_STRING", "")

# Configure logging for the default logger and for the `azure` logger.
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
LOGGER.addHandler(handler)

# Set the logging level for all azure-* libraries (the azure-storage-blob library uses this one).
# Reference: https://learn.microsoft.com/en-us/azure/developer/python/sdk/azure-sdk-logging
azure_logger = logging.getLogger("azure")
azure_logger.setLevel(logging.WARNING)


def get_model(model_name: str = "tiny.en", **kwargs) -> whisper.model.Whisper:
    """Return (download if needed) the requested Whisper model (default model download
    location is ~/.cache/whisper).
    Reference: https://github.com/openai/whisper/blob/main/whisper/__init__.py#L103
    """
    return whisper.load_model(name=model_name, **kwargs)


def get_transcription(model: whisper.model.Whisper, **kwargs) -> dict | None:
    """Transcribe an audio file using a Whisper model, and return a dictionary
    containing the resulting text and segment-level details.
    Reference: https://github.com/openai/whisper/blob/main/whisper/transcribe.py#L38

    Discussion related to tuning transcription output: https://github.com/openai/whisper/discussions/192
    """
    try:
        return model.transcribe(**kwargs)
    except RuntimeError:
        LOGGER.warning(f"{kwargs['audio']} could not be processed")
        return None


def write_transcription(transcription: dict, name: str, output_format: str = "tsv", output_dir: str = "transcripts") -> bool:
    """For the passed-in transcription dict and name, writes an output file of
    the nominated format into `output_dir`."""
    writer = get_writer(output_format, output_dir)
    writer(result=transcription, audio_path=f"{name}.{output_format}")
    return True


def get_audio_paths(conn_str: str, container_name: str, prefix: Optional[str] = None) -> List[str]:
    """
    Check Azure blob storage for the list of uploaded audio files, returns a
    list of paths.
    """
    try:
        container_client = ContainerClient.from_connection_string(conn_str, container_name)
        if prefix:
            blob_list = container_client.list_blobs(name_starts_with=prefix)
        else:
            blob_list = container_client.list_blobs()
        remote_blobs = [blob.name for blob in blob_list]
    except ResourceNotFoundError:
        remote_blobs = []

    return remote_blobs


if __name__ == "__main__":
    """
    Imputs:
        - Azure container of input audio files
        - Model name (optional)
        - Transcript format (optional)
        - Output container of transcript files (optional)

    Outputs:
        - Transcript files of the nominated format in the output container
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--container",
        help="Blob container of input audio files",
        action="store",
        required=True,
    )
    parser.add_argument(
        "-p",
        "--prefix",
        help="Prefix string for filtering input audio files (optional)",
        action="store",
        required=False,
    )
    parser.add_argument(
        "-m",
        "--model",
        help="Whisper speech recognition model name to use (optional)",
        default="tiny.en",
        action="store",
        required=False,
    )
    parser.add_argument(
        "-f",
        "--format",
        help="Transcript output format (optional)",
        default="tsv",
        action="store",
        required=False,
    )
    parser.add_argument(
        "-d",
        "--dest-container",
        help="Destination blob container for transcript files (optional)",
        action="store",
        required=False,
    )
    args = parser.parse_args()

    input_container_name = args.container
    prefix = str(args.prefix)
    model_name = args.model
    output_format = args.format

    if not args.dest_container:
        # Set the destination container to be the same as the source.
        output_container_name = input_container_name
    else:
        output_container_name = args.dest_container

    LOGGER.info(f"Instantiating {model_name} model")
    model = get_model(model_name)

    # First, get a directory listing for the nominated input container.
    audio_paths = get_audio_paths(conn_str=CONN_STR, container_name=input_container_name, prefix=prefix)
    audio_extensions = [".mp3", ".m4a"]  # TODO: don't hardcode this list.

    LOGGER.info(f"Processing {len(audio_paths)} files")

    for blob_path in audio_paths:
        audio_filename = os.path.basename(blob_path)
        audio_path = os.path.dirname(blob_path)
        name, ext = os.path.splitext(audio_filename)
        if ext.lower() not in audio_extensions:
            LOGGER.info(f"Skipping {blob_path}")
            continue  # Skip non-audio files.

        # Download the audio file locally to the temp directory.
        tmp_dir = TemporaryDirectory()
        dest_path = Path(os.path.join(tmp_dir.name, audio_path))
        dest_path.mkdir(parents=True, exist_ok=True)
        dest_file = dest_path.joinpath(audio_filename)
        downloaded_blob = open(dest_file, "wb")
        blob_client = BlobClient.from_connection_string(CONN_STR, input_container_name, blob_path)

        LOGGER.info(f"Downloading {blob_path}")
        download_stream = blob_client.download_blob()
        downloaded_blob.write(download_stream.readall())

        # Get the transcript for this downloaded audio file.
        LOGGER.info(f"Transcribing {dest_file}")
        transcription = get_transcription(model=model, audio=str(dest_file))
        if not transcription:
            LOGGER.warning(f"Unable to get transcription for {dest_file}")
            continue

        # Write the transcription.
        transcription_file = f"{name}.{output_format}"
        transcription_path = os.path.join(dest_path, transcription_file)
        LOGGER.info(f"Writing transcription to {transcription_path}")

        output_dir = str(dest_path)
        transcription_result = write_transcription(transcription, name, output_format, output_dir)

        # Upload the transcription file to the container.
        uploaded_transcription_path = os.path.join(audio_path, transcription_file)
        LOGGER.info(f"Uploading transcription to {uploaded_transcription_path}")
        blob_client = BlobClient.from_connection_string(CONN_STR, output_container_name, uploaded_transcription_path)
        source_data = open(transcription_path, "rb")
        blob_client.upload_blob(source_data, overwrite=True)
