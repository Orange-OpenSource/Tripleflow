#  
# Software Name : Tripleflow
# SPDX-FileCopyrightText: Copyright (c) Orange SA
# SPDX-License-Identifier: MIT
# 
# This software is distributed under the MIT License,
# see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
# 
# Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
# Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  
#

FROM python:3.11.2

ARG MONGO_URI=""
ENV MONGO_URI=$MONGO_URI

ARG CORS_ORIGINS=""
ENV CORS_ORIGINS=$CORS_ORIGINS

RUN pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.13.0 torchvision==0.28.0

RUN pip install --no-cache-dir -r requirements.txt

ENV DOCLING_ARTIFACTS_PATH=/opt/docling-models
RUN docling-tools models download -o /opt/docling-models layout tableformer
ENV HF_HUB_OFFLINE=1

RUN pip install --no-cache-dir opencv-python-headless

COPY . .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


EXPOSE 5981

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5981"]
