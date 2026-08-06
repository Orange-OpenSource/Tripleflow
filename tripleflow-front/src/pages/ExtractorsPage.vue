<!--  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

-->

<template>
    <main class="app-content extractors-page">
        <div class="page-intro">
            <p class="eyebrow mb-2">Extraction Workspace</p>
            <h1 class="mb-2">Extractors</h1>
            <p class="page-subtitle mb-0">
                Register your own extractor so it shows up on the extraction page. TripleFlow stores the
                configuration and calls your endpoint at extraction time.
            </p>
        </div>

        <div class="extractors-layout">
            <!-- Registered extractors -->
            <section class="panel">
                <h2 class="h5 mb-3">Registered extractors</h2>

                <p v-if="isLoading" class="text-muted">Loading…</p>

                <p v-if="loadError" class="load-warning">
                    Extractors could not be loaded ({{ loadError }}). Check that the backend is running.
                </p>

                <p v-if="!isLoading && !loadError && availableExtractors.length === 0" class="text-muted">
                    No extractor registered yet. Add one with the form on the right.
                </p>

                <ul class="extractor-list">
                    <li v-for="extractor in availableExtractors" :key="extractor.id" class="extractor-item">
                        <div class="extractor-item-main">
                            <span class="extractor-item-label">{{ extractor.label || extractor.id }}</span>
                        </div>
                        <code class="extractor-item-id">{{ extractor.id }}</code>
                        <p v-if="extractor.description" class="extractor-item-desc">{{ extractor.description }}</p>

                        <button
                            type="button"
                            class="extractor-delete-btn"
                            :disabled="deletingId === extractor.id"
                            @click="onDelete(extractor)"
                        >
                            {{ deletingId === extractor.id ? 'Removing…' : 'Remove' }}
                        </button>
                    </li>
                </ul>

                <p v-if="deleteError" class="field-error">{{ deleteError }}</p>
            </section>

            <!-- Add extractor form -->
            <section class="panel">
                <h2 class="h5 mb-1">Add an extractor</h2>
                <p class="text-muted small mb-3">
                    The backend will call this endpoint and is responsible for fetching it — do not register
                    untrusted URLs on a shared instance.
                </p>

                <div v-if="successMessage" class="alert alert-success" role="alert">
                    {{ successMessage }}
                </div>

                <ExtractorForm
                    ref="formRef"
                    :existingIds="existingIds"
                    :submitting="submitting"
                    :createError="createError"
                    :testing="testing"
                    :testError="testError"
                    :testResult="testResult"
                    @submit="onAdd"
                    @test="onTest"
                />
            </section>
        </div>
    </main>
</template>

<script setup>
/**
 * Management page for custom extractors: lists built-in and registered extractors,
 * lets the user add a new one through ExtractorForm, test it against a sample text,
 * and remove custom ones.
 */
import { onMounted, ref } from 'vue'
import ExtractorForm from '../components/molecules/ExtractorForm.vue'
import { testExtractor } from '../composables/extractors/api'
import { useExtractors } from '../composables/extractors/useExtractors'

const {
    availableExtractors,
    existingIds,
    isLoading,
    loadError,
    loadExtractors,
    addExtractor,
    removeExtractor,
} = useExtractors()

const formRef = ref(null)

const submitting = ref(false)
const createError = ref('')
const successMessage = ref('')

const testing = ref(false)
const testError = ref('')
const testResult = ref(null)

const deletingId = ref('')
const deleteError = ref('')

onMounted(loadExtractors)

/** Registers a new extractor and resets the form on success. */
async function onAdd(config) {
    submitting.value = true
    createError.value = ''
    successMessage.value = ''

    try {
        await addExtractor(config)
        successMessage.value = `Extractor "${config.label}" added.`
        testResult.value = null
        testError.value = ''
        formRef.value?.resetForm()
    } catch (error) {
        createError.value = error.message || 'Failed to add the extractor.'
    } finally {
        submitting.value = false
    }
}

/** Runs a dry-run of the configuration against the sample text. */
async function onTest({ config, sampleText }) {
    testing.value = true
    testError.value = ''
    testResult.value = null

    try {
        const result = await testExtractor({ config, sample_text: sampleText })
        testResult.value = Array.isArray(result.triples) ? result.triples : []
    } catch (error) {
        testError.value = error.message || 'The test request failed.'
    } finally {
        testing.value = false
    }
}

/** Deletes a custom extractor after confirmation. */
async function onDelete(extractor) {
    if (!window.confirm(`Remove the extractor "${extractor.label || extractor.id}"?`)) {
        return
    }

    deletingId.value = extractor.id
    deleteError.value = ''

    try {
        await removeExtractor(extractor.id)
    } catch (error) {
        deleteError.value = error.message || 'Failed to remove the extractor.'
    } finally {
        deletingId.value = ''
    }
}
</script>

<style scoped>
.extractors-page {
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

.extractors-layout {
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

.extractor-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.extractor-item {
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.4rem;
    padding: 0.75rem;
}

.extractor-item-main {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
}

.extractor-item-label {
    font-weight: 700;
}

.extractor-item-id {
    font-size: 0.8rem;
    color: var(--ods-gray-700);
}

.extractor-item-desc {
    font-size: 0.85rem;
    color: var(--ods-gray-700);
    margin: 0.35rem 0 0;
}

.extractor-delete-btn {
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

.extractor-delete-btn:hover:not(:disabled) {
    border-color: #cd3c14;
    background: rgba(205, 60, 20, 0.06);
}

.extractor-delete-btn:disabled {
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
    .extractors-layout {
        grid-template-columns: 1fr;
        padding: 1rem;
    }
}
</style>
