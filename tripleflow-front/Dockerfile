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

FROM node:24 AS build

ARG VITE_TRIPLEFLOW_API_URL=""
ENV VITE_TRIPLEFLOW_API_URL=$VITE_TRIPLEFLOW_API_URL

ARG VITE_TTL_BASE_URL=""
ENV VITE_TTL_BASE_URL=$VITE_TTL_BASE_URL

ARG VITE_FOOTER_LINKS=""
ENV VITE_FOOTER_LINKS=$VITE_FOOTER_LINKS

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

RUN npm install -g serve

EXPOSE 80

CMD ["serve", "-s", "dist", "-l", "80"]
