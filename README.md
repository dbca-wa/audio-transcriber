# Audio Transcriber

A basic project to make use of the OpenAI Whisper general-purpose speech recognition model to transcribe audio files.

Reference: <https://github.com/openai/whisper>

The `transcriber` function expects to be passed a model name to use, a blob container of input audio files, and (optionally) an output blob container for transcripts.

## Installation

The recommended way to set up this project for development is using
[Poetry](https://python-poetry.org/docs/) to install and manage a virtual Python
environment. With Poetry installed, change into the project directory and run:

    poetry install

Activate the virtualenv like so:

    poetry shell

To run Python commands in the activated virtualenv, thereafter run them as normal:

    python manage.py

Manage new or updating project dependencies with Poetry also, like so:

    poetry add newpackage==1.0

## Environment variables

This project uses confy to set environment variables (in a `.env` file).
The following variables are required for the project to run:

    AZURE_CONNECTION_STRING=AzureStorageAccountConnectionString

## Running

Run locally like so:

    python transcriber.py --help
