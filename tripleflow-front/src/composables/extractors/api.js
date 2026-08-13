/*
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT

This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html

Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.

*/

import { buildErrorMessage, readJson } from '../apiError'
import { DEFAULT_API_BASE_URL } from '../extraction/constants'

const apiBaseUrl = (import.meta.env.VITE_TRIPLEFLOW_API_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')

/**
 * Fetches the list of custom extractors registered on the backend.
 * @returns {Promise<object[]>}
 */
export async function fetchExtractors() {
    const response = await fetch(`${apiBaseUrl}/extractors`)
    if (!response.ok) {
        throw new Error(buildErrorMessage(await readJson(response), 'Failed to fetch extractors'))
    }
    const data = await response.json()
    return data.extractors ?? data
}

/**
 * Registers a new custom extractor.
 * @param {object} config - extractor configuration (id, label, endpoint, output_mapping, knowledge_base)
 * @returns {Promise<object>}
 */
export async function createExtractor(config) {
    const response = await fetch(`${apiBaseUrl}/extractors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
    })
    if (!response.ok) {
        throw new Error(buildErrorMessage(await readJson(response), 'Failed to create the extractor'))
    }
    return response.json()
}

/**
 * Deletes a custom extractor by its identifier.
 * @param {string} id
 * @returns {Promise<void>}
 */
export async function deleteExtractor(id) {
    const response = await fetch(`${apiBaseUrl}/extractors/${encodeURIComponent(id)}`, {
        method: 'DELETE',
    })
    if (!response.ok) {
        throw new Error(buildErrorMessage(await readJson(response), 'Failed to delete the extractor'))
    }
}

/**
 * Runs a dry-run of an extractor configuration against a sample text without saving it.
 * The backend calls the configured endpoint, applies the output mapping, and returns the
 * resulting triples so the user can verify the configuration before registering it.
 * @param {{ config: object, sample_text: string }} params
 * @returns {Promise<{ triples: object[] }>}
 */
export async function testExtractor({ config, sample_text }) {
    const response = await fetch(`${apiBaseUrl}/extractors/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config, sample_text }),
    })
    if (!response.ok) {
        throw new Error(buildErrorMessage(await readJson(response), 'The test request failed'))
    }
    const data = await response.json()
    return {
        triples: data.triples ?? data.result?.triples ?? data.result ?? [],
    }
}
