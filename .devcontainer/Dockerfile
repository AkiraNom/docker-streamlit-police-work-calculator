# define python version
FROM mcr.microsoft.com/vscode/devcontainers/python:3.11

# set working directory
WORKDIR /app

# install dependencies
COPY ./requirements.txt ./

RUN pip install --no-cache-dir --upgrade -r requirements.txt
RUN python -m ipykernel install --user

