/*  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

*/

import { computed, ref } from 'vue'

import {
    createExtractor as apiCreateExtractor,
    deleteExtractor as apiDeleteExtractor,
    fetchExtractors,
} from './api'

let extractorsState = null

/**
 * Creates the shared, reactive extractors state. The list of user-registered
 * extractors is served by the backend through GET /extractors, each entry
 * carrying its `knowledge_base` config used for entity links.
 */
function createExtractorsState() {
    const extractors = ref([])
    const isLoading = ref(false)
    const loadError = ref('')
    const hasLoaded = ref(false)

    const availableExtractors = computed(() => extractors.value)

    const extractorOptions = computed(() =>
        availableExtractors.value.map((extractor) => ({
            value: extractor.id,
            label: extractor.label || extractor.id,
        }))
    )

    const existingIds = computed(() => availableExtractors.value.map((extractor) => extractor.id))

    /** Loads the extractor list from the backend. */
    async function loadExtractors() {
        isLoading.value = true
        loadError.value = ''

        try {
            const list = await fetchExtractors()
            extractors.value = Array.isArray(list)
                ? list.filter((extractor) => extractor?.id)
                : []
        } catch (error) {
            loadError.value = error.message || 'Unable to load extractors.'
            extractors.value = []
        } finally {
            isLoading.value = false
            hasLoaded.value = true
        }
    }

    /** Registers a new custom extractor, then refreshes the list. */
    async function addExtractor(config) {
        const created = await apiCreateExtractor(config)
        await loadExtractors()
        return created
    }

    /** Deletes a custom extractor by id, then refreshes the list. */
    async function removeExtractor(id) {
        await apiDeleteExtractor(id)
        await loadExtractors()
    }

    return {
        availableExtractors,
        extractorOptions,
        existingIds,
        isLoading,
        loadError,
        hasLoaded,
        loadExtractors,
        addExtractor,
        removeExtractor,
    }
}

/**
 * Vue composable returning the shared extractors state (singleton across all consumers).
 * @returns {ReturnType<typeof createExtractorsState>}
 */
export function useExtractors() {
    if (!extractorsState) {
        extractorsState = createExtractorsState()
    }

    return extractorsState
}
