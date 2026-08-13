<template>
    <main class="app-content targets-page">
        <div class="page-intro">
            <p class="eyebrow mb-2">Publication</p>
            <h1 class="mb-2">Targets</h1>
            <p class="page-subtitle mb-0">
                Register the knowledge graph your validated triples are pushed to. TripleFlow stores the
                configuration and sends a SPARQL <code>INSERT DATA</code> to its update endpoint from the
                Validation page.
            </p>
        </div>

        <div class="targets-layout">
            <!-- Registered targets -->
            <section class="panel">
                <h2 class="h5 mb-3">Registered targets</h2>

                <p v-if="isLoading" class="text-muted">Loading…</p>

                <p v-if="loadError" class="load-warning">
                    Targets could not be loaded ({{ loadError }}). Check that the backend is running.
                </p>

                <p v-if="!isLoading && !loadError && availableSinks.length === 0" class="text-muted">
                    No target registered yet. Add one with the form on the right.
                </p>

                <ul class="target-list">
                    <li v-for="sink in availableSinks" :key="sink.id" class="target-item">
                        <div class="target-item-main">
                            <span class="target-item-label">{{ sink.label || sink.id }}</span>
                            <span class="target-auth-badge">{{ authLabel(sink) }}</span>
                        </div>
                        <code class="target-item-id">{{ sink.id }}</code>
                        <p v-if="sink.description" class="target-item-desc">{{ sink.description }}</p>
                        <p class="target-item-url" :title="targetUrl(sink)">{{ targetUrl(sink) }}</p>
                        <p class="target-item-graph">
                            written via: {{ sink.type === 'http' ? `its own API (${sink.request_method || 'POST'} per triple)` : 'SPARQL update' }}
                        </p>
                        <p v-if="sink.prepare_steps?.length" class="target-item-graph">
                            before publishing: {{ sink.prepare_steps.join(', ') }}
                        </p>
                        <p v-if="sink.graph_uri" class="target-item-graph" :title="sink.graph_uri">
                            graph: {{ sink.graph_uri }}
                        </p>
                        <p v-if="sink.type !== 'http'" class="target-item-graph">
                            body: {{ bodyFormatLabel(sink.body_format) }}
                        </p>
                        <p v-if="sink.header_names?.length" class="target-item-graph">
                            headers: {{ sink.header_names.join(', ') }}
                        </p>
                        <p class="target-item-graph">anchoring: {{ anchoringLabel(sink) }}</p>

                        <button
                            type="button"
                            class="target-delete-btn"
                            :disabled="deletingId === sink.id"
                            @click="onDelete(sink)"
                        >
                            {{ deletingId === sink.id ? 'Removing…' : 'Remove' }}
                        </button>
                    </li>
                </ul>

                <p v-if="deleteError" class="field-error">{{ deleteError }}</p>
            </section>

            <!-- Add target form -->
            <section class="panel">
                <h2 class="h5 mb-1">Add a target</h2>
                <p class="text-muted small mb-3">
                    The backend writes to this endpoint on your behalf — only register graphs you are
                    allowed to write to.
                </p>

                <div v-if="successMessage" class="alert alert-success" role="alert">
                    {{ successMessage }}
                </div>

                <SinkForm
                    ref="formRef"
                    :existingIds="existingIds"
                    :submitting="submitting"
                    :createError="createError"
                    @submit="onAdd"
                />
            </section>
        </div>
    </main>
</template>

<script setup>
/**
 * Management page for publication targets: lists registered SPARQL UPDATE endpoints,
 * lets the user add one through SinkForm, and remove them.
 */
import { onMounted, ref } from 'vue'
import SinkForm from '../components/molecules/SinkForm.vue'
import { useSinks } from '../composables/sinks/useSinks'

const {
    availableSinks,
    existingIds,
    isLoading,
    loadError,
    loadSinks,
    addSink,
    removeSink,
} = useSinks()

const formRef = ref(null)

const submitting = ref(false)
const createError = ref('')
const successMessage = ref('')

const deletingId = ref('')
const deleteError = ref('')

const AUTH_LABELS = {
    none: 'No auth',
    basic: 'Basic auth',
    header: 'Token',
}

const BODY_FORMAT_LABELS = {
    'sparql-update': 'application/sparql-update',
    'form-urlencoded': 'form-encoded (update=…)',
}

onMounted(loadSinks)

/**
 * Renders a target's authentication as a short badge label. Headers can now carry the
 * credential on their own, so a target with no auth method but a header is not "No auth".
 */
function authLabel(sink) {
    if (sink.auth_type && sink.auth_type !== 'none') {
        return AUTH_LABELS[sink.auth_type]
    }
    return sink.header_names?.length ? 'Header auth' : AUTH_LABELS.none
}

/** The endpoint written to, whichever kind of target this is. */
function targetUrl(sink) {
    return sink.type === 'http' ? sink.request_url : sink.update_url
}

/** Renders how the update travels in the request body. */
function bodyFormatLabel(bodyFormat) {
    return BODY_FORMAT_LABELS[bodyFormat] || BODY_FORMAT_LABELS['sparql-update']
}

/** Renders where the identifiers published to this target can be browsed. */
function anchoringLabel(sink) {
    const kb = sink.knowledge_base
    if (kb?.type === 'wikidata') {
        return 'Wikidata'
    }
    if (kb?.type === 'wikibase' && kb.base_url) {
        return kb.base_url
    }
    return 'none — published ids stay unlinked'
}

/** Registers a new target and resets the form on success. */
async function onAdd(config) {
    submitting.value = true
    createError.value = ''
    successMessage.value = ''

    try {
        await addSink(config)
        successMessage.value = `Target "${config.label}" added.`
        formRef.value?.resetForm()
    } catch (error) {
        createError.value = error.message || 'Failed to add the target.'
    } finally {
        submitting.value = false
    }
}

/** Deletes a target after confirmation. */
async function onDelete(sink) {
    if (!window.confirm(`Remove the target "${sink.label || sink.id}"?`)) {
        return
    }

    deletingId.value = sink.id
    deleteError.value = ''

    try {
        await removeSink(sink.id)
    } catch (error) {
        deleteError.value = error.message || 'Failed to remove the target.'
    } finally {
        deletingId.value = ''
    }
}
</script>

<style scoped>
.targets-page {
    --ods-orange-100: #ff7900;
    --ods-white-100: #fff;
    --ods-gray-300: #ddd;
    --ods-gray-700: #595959;

    width: 100%;
    min-height: calc(100vh - 5rem);
    background: var(--ods-white-100);
}

.page-intro {
    padding: 2rem 1.5rem 1.5rem;
    border-bottom: 0.1rem solid var(--ods-gray-300);
}

.eyebrow {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--ods-gray-700);
    font-weight: 700;
}

.page-subtitle {
    max-width: 44rem;
    color: var(--ods-gray-700);
}

.targets-layout {
    display: grid;
    grid-template-columns: minmax(16rem, 22rem) minmax(0, 1fr);
    gap: 1.5rem;
    align-items: start;
    padding: 1.5rem;
}

.panel {
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.5rem;
    padding: 1.5rem;
    background: var(--ods-white-100);
    box-shadow: 0 1rem 2.5rem rgba(0, 0, 0, 0.05);
}

.target-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.target-item {
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.4rem;
    padding: 0.75rem;
}

.target-item-main {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
}

.target-item-label {
    font-weight: 700;
}

.target-auth-badge {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--ods-gray-700);
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.2rem;
    padding: 0.1rem 0.35rem;
    white-space: nowrap;
}

.target-item-id {
    font-size: 0.8rem;
    color: var(--ods-gray-700);
}

.target-item-desc {
    font-size: 0.85rem;
    color: var(--ods-gray-700);
    margin: 0.35rem 0 0;
}

.target-item-url,
.target-item-graph {
    font-size: 0.75rem;
    color: var(--ods-gray-700);
    margin: 0.35rem 0 0;
    overflow-wrap: anywhere;
}

.target-delete-btn {
    margin-top: 0.5rem;
    border: 0.1rem solid var(--ods-gray-300);
    background: transparent;
    color: #cd3c14;
    border-radius: 0.3rem;
    padding: 0.2rem 0.7rem;
    font-size: 0.8rem;
    cursor: pointer;
    transition: border-color 0.15s, background-color 0.15s;
}

.target-delete-btn:hover:not(:disabled) {
    border-color: #cd3c14;
    background: rgba(205, 60, 20, 0.06);
}

.target-delete-btn:disabled {
    opacity: 0.5;
    cursor: default;
}

.load-warning {
    font-size: 0.85rem;
    color: #8a6d00;
    background: #fff6e0;
    border-radius: 0.4rem;
    padding: 0.5rem 0.75rem;
}

.field-error {
    font-size: 0.8rem;
    font-weight: 600;
    color: #cd3c14;
    margin-top: 0.5rem;
}

@media (max-width: 62rem) {
    .targets-layout {
        grid-template-columns: 1fr;
        padding: 1rem;
    }
}
</style>
