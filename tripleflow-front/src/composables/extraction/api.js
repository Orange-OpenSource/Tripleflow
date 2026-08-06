/*  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

*/

import { BACKEND_ERROR_PREFIX, DEFAULT_API_BASE_URL } from './constants'

const apiBaseUrl = (import.meta.env.VITE_TRIPLEFLOW_API_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')

/** Converts a FastAPI validation error location array into a dot-separated string. */
function stringifyValidationLocation(location) {
    if (!Array.isArray(location) || location.length === 0) {
        return ''
    }

    return location.join('.')
}

/**
 * Recursively extracts a readable error message from any value type.
 * Handles strings, numbers, arrays, and nested objects (including FastAPI detail arrays).
 * @param {*} value
 * @returns {string|null}
 */
function extractMessage(value) {
    if (typeof value === 'string') {
        const trimmedValue = value.trim()
        return trimmedValue || null
    }

    if (typeof value === 'number' || typeof value === 'boolean') {
        return String(value)
    }

    if (Array.isArray(value)) {
        const messages = value
            .map((item) => extractMessage(item))
            .filter(Boolean)

        return messages.length > 0 ? messages.join(' | ') : null
    }

    if (!value || typeof value !== 'object') {
        return null
    }

    if (Array.isArray(value.detail)) {
        const validationMessages = value.detail
            .map((item) => {
                if (!item || typeof item !== 'object') {
                    return extractMessage(item)
                }

                const location = stringifyValidationLocation(item.loc)
                const message = extractMessage(item.msg ?? item.message ?? item.detail ?? item.error)

                if (!message) {
                    return null
                }

                return location ? `${location}: ${message}` : message
            })
            .filter(Boolean)

        if (validationMessages.length > 0) {
            return validationMessages.join(' | ')
        }
    }

    const nestedMessage = extractMessage(
        value.message
        ?? value.detail
        ?? value.error
        ?? value.msg
        ?? value.title
        ?? value.description
    )

    if (nestedMessage) {
        return nestedMessage
    }

    const objectEntries = Object.entries(value)
        .map(([key, nestedValue]) => {
            const message = extractMessage(nestedValue)
            return message ? `${key}: ${message}` : null
        })
        .filter(Boolean)

    return objectEntries.length > 0 ? objectEntries.join(' | ') : null
}

/** Removes all HTML tags from a string, replacing them with a space. */
function stripHtmlTags(value) {
    return value.replace(/<[^>]*>/g, ' ')
}

/** Replaces common HTML entities with their plain-text equivalents. */
function decodeHtmlEntities(value) {
    const entities = {
        '&quot;': '"',
        '&#39;': "'",
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&nbsp;': ' ',
    }

    return value.replace(/&quot;|&#39;|&amp;|&lt;|&gt;|&nbsp;/g, (entity) => entities[entity] || entity)
}

/** Collapses consecutive whitespace characters into a single space and trims the result. */
function normalizeWhitespace(value) {
    return value.replace(/\s+/g, ' ').trim()
}

/**
 * Cleans a raw backend response string (which may be an HTML error page) into a short, readable message.
 * Returns null if the input is empty or not a string.
 * @param {*} responseText
 * @returns {string|null}
 */
function sanitizeErrorResponseText(responseText) {
    if (typeof responseText !== 'string') {
        return null
    }

    const trimmedText = responseText.trim()

    if (!trimmedText) {
        return null
    }

    const normalizedText = normalizeWhitespace(decodeHtmlEntities(stripHtmlTags(trimmedText)))

    if (!normalizedText) {
        return null
    }

    if (normalizedText.includes('UnboundLocalError') && normalizedText.includes("variable 'response'")) {
        return 'Extractor backend error: internal server variable "response" was used before being initialized.'
    }

    if (normalizedText.includes('Werkzeug Debugger')) {
        return 'Extractor backend error: server returned a Werkzeug debug page instead of a normal API response.'
    }

    return normalizedText.slice(0, 300)
}

/**
 * Reads the response body as text and parses it as JSON.
 * Throws a descriptive error if parsing fails or the response is not OK.
 * @param {Response} response
 * @returns {Promise<object|null>}
 */
async function parseExtractionResponse(response) {
    const responseText = await response.text()

    if (!responseText) {
        return null
    }

    try {
        return JSON.parse(responseText)
    } catch {
        if (!response.ok) {
            throw new Error(
                sanitizeErrorResponseText(responseText) || 'Backend returned an unreadable error response.'
            )
        }

        throw new Error('Backend returned an unexpected response format.')
    }
}

/**
 * Returns the best human-readable error message from an error response body,
 * falling back to a generic message mentioning the extractor name.
 * @param {*} data
 * @param {string} extractor
 * @returns {string}
 */
function getErrorMessage(data, extractor) {
    return extractMessage(data) || `${BACKEND_ERROR_PREFIX} ${extractor}.`
}

/**
 * Builds the POST body for the /extract endpoint.
 * Uses the batch form (texts array) when more than one text is provided,
 * otherwise uses the single-text form.
 */
function buildExtractionRequestBody({ extractor, text, texts, file_name, file_names }) {
    if (Array.isArray(texts) && texts.length > 1) {
        return {
            texts,
            extractor,
            ...(Array.isArray(file_names) && file_names.some(Boolean) && { file_names }),
        }
    }

    return {
        text,
        extractor,
        ...(file_name && { file_name }),
    }
}

/**
 * Sends a POST request to /extract and returns the raw response and parsed body.
 * @param {string} extractor - extractor identifier
 * @param {{ text: string, texts: string[], file_name?: string, file_names?: string[] }} payload
 * @returns {Promise<{ response: Response, data: object }>}
 */
async function requestExtraction(extractor, { text, texts, file_name, file_names }) {
    const response = await fetch(`${apiBaseUrl}/extract`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(buildExtractionRequestBody({ extractor, text, texts, file_name, file_names })),
    })
    const data = await parseExtractionResponse(response)

    return { response, data }
}

/**
 * Calls the extraction API and returns the parsed response data.
 * Throws an Error with a readable message if the request fails.
 * @param {{ extractor: string, text: string, texts?: string[], file_name?: string, file_names?: string[] }} params
 * @returns {Promise<{ data: object, responseTimestamp: string|null }>}
 */
export async function fetchExtraction({ extractor, text, texts, file_name, file_names }) {
    const request = await requestExtraction(extractor, { text, texts, file_name, file_names })

    if (request.response.ok) {
        const responseTimestamp = request.response.headers.get('date')
        return {
            data: request.data,
            responseTimestamp: responseTimestamp || null,
        }
    }

    throw new Error(getErrorMessage(request.data, extractor))
}
