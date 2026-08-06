/*  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

*/

/**
 * Backend API base URL. Deployment-specific hosts belong in the VITE_TRIPLEFLOW_API_URL
 * env var (.env / .env.production), never in code; the default targets a local backend.
 */
export const DEFAULT_API_BASE_URL = (
    import.meta.env.VITE_TRIPLEFLOW_API_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '')
export const SUPPORTED_FILE_ERROR = 'Only .txt and .pdf files are supported.'
export const FILE_READ_ERROR = 'Unable to read one of the selected files.'
export const INPUT_REQUIRED_ERROR = 'Please enter text or upload at least one file first.'
export const EXTRACTOR_REQUIRED_ERROR = 'Please select at least one extractor.'
export const BACKEND_ERROR_PREFIX = 'Error contacting backend for'
