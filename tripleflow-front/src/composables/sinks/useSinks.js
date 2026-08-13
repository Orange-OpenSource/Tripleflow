import { computed, ref } from 'vue'

import {
    createSink as apiCreateSink,
    deleteSink as apiDeleteSink,
    fetchSinks,
} from './api'

let sinksState = null

/**
 * Creates the shared, reactive state for publication targets. Targets are served
 * by the backend through GET /sinks; the credentials they use to reach their
 * SPARQL endpoint stay on the backend and are never part of this state.
 */
function createSinksState() {
    const sinks = ref([])
    const isLoading = ref(false)
    const loadError = ref('')
    const hasLoaded = ref(false)

    const availableSinks = computed(() => sinks.value)

    const sinkOptions = computed(() =>
        availableSinks.value.map((sink) => ({
            value: sink.id,
            label: sink.label || sink.id,
        }))
    )

    const existingIds = computed(() => availableSinks.value.map((sink) => sink.id))

    /** Loads the target list from the backend. */
    async function loadSinks() {
        isLoading.value = true
        loadError.value = ''

        try {
            const list = await fetchSinks()
            sinks.value = Array.isArray(list) ? list.filter((sink) => sink?.id) : []
        } catch (error) {
            loadError.value = error.message || 'Unable to load targets.'
            sinks.value = []
        } finally {
            isLoading.value = false
            hasLoaded.value = true
        }
    }

    /** Registers a new target, then refreshes the list. */
    async function addSink(config) {
        const created = await apiCreateSink(config)
        await loadSinks()
        return created
    }

    /** Deletes a target by id, then refreshes the list. */
    async function removeSink(id) {
        await apiDeleteSink(id)
        await loadSinks()
    }

    return {
        availableSinks,
        sinkOptions,
        existingIds,
        isLoading,
        loadError,
        hasLoaded,
        loadSinks,
        addSink,
        removeSink,
    }
}

/**
 * Vue composable returning the shared publication-targets state (singleton across all consumers).
 * @returns {ReturnType<typeof createSinksState>}
 */
export function useSinks() {
    if (!sinksState) {
        sinksState = createSinksState()
    }

    return sinksState
}
