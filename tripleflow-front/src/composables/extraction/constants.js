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
/**
 * Formats accepted as extraction input, whichever parsing mode is active.
 * Deliberately limited to plain text and PDF: those are the sources the pipeline
 * is documented and evaluated on, and every other format would widen the surface
 * without widening what can actually be extracted from it.
 *
 * The parsing toggle does not change this list, only how a PDF is read: Docling
 * on the backend (structured Markdown, tables, page provenance) or pdf.js in the
 * browser. Keep in sync with DOCLING_EXTENSIONS on the backend.
 */
export const SUPPORTED_FILE_EXTENSIONS = ['.txt', '.pdf']
export const SUPPORTED_FILE_ACCEPT = '.txt,.pdf,text/plain,application/pdf'
export const UNSUPPORTED_FILE_ERROR = 'Only .txt and .pdf files are supported.'

export const FILE_READ_ERROR = 'Unable to read one of the selected files.'
export const PARSE_REQUEST_ERROR =
    'Could not parse this document on the server. It may exceed the upload limit — turn off document parsing to read it in the browser instead.'
export const INPUT_REQUIRED_ERROR = 'Please enter text or upload at least one file first.'
export const EXTRACTOR_REQUIRED_ERROR = 'Please select at least one extractor.'
export const BACKEND_ERROR_PREFIX = 'Error contacting backend for'
