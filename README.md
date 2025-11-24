# Audio Transcriber

A basic project to make use of the OpenAI Whisper general-purpose speech recognition model to transcribe audio files.

Reference: <https://github.com/openai/whisper>

The `transcriber` function expects to be passed a model name to use, a blob container of input audio files, and (optionally) an output blob container for transcripts.

## Installation

Dependencies for this project are managed using [uv](https://docs.astral.sh/uv/).
With uv installed, change into the project directory and run:

    uv sync

Activate the virtualenv like so:

    source .venv/bin/activate

To run Python commands in the activated virtualenv, thereafter run them like so:

    python manage.py

Manage new or updated project dependencies with uv also, like so:

    uv add newpackage==1.0

## Environment variables

This project uses **python-dotenv** to set environment variables (in a `.env` file).
The following variables are required for the project to run:

    AZURE_CONNECTION_STRING=AzureStorageAccountConnectionString

## Running

Run locally like so:

    python transcriber.py --help

## Docker image build

Build and push a multi-architecture-capable image from the `Dockerfile` like so:

    docker buildx create --name container-builder --driver docker-container --use --bootstrap
    docker buildx build --push --platform linux/amd64,linux/arm64 -t ghcr.io/dbca-wa/audio-transcriber .
