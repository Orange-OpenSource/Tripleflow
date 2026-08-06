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
    <form class="extractor-form" @submit.prevent="onSubmit">
        <!-- Identity -->
        <fieldset class="form-section">
            <legend class="form-section-title">Identity</legend>

            <div class="row g-3">
                <div class="col-md-6">
                    <label for="extractor-id" class="form-label fw-bold">Slug</label>
                    <input
                        id="extractor-id"
                        v-model="form.id"
                        type="text"
                        class="form-control"
                        :class="{ 'is-invalid': errors.id }"
                        placeholder="my-extractor"
                        autocomplete="off"
                    />
                    <p class="field-hint">Lowercase technical id sent as <code>extractor</code> to the API.</p>
                    <p v-if="errors.id" class="field-error">{{ errors.id }}</p>
                </div>

                <div class="col-md-6">
                    <label for="extractor-label" class="form-label fw-bold">Display name</label>
                    <input
                        id="extractor-label"
                        v-model="form.label"
                        type="text"
                        class="form-control"
                        :class="{ 'is-invalid': errors.label }"
                        placeholder="My Extractor"
                    />
                    <p v-if="errors.label" class="field-error">{{ errors.label }}</p>
                </div>

                <div class="col-12">
                    <label for="extractor-description" class="form-label fw-bold">Description <span class="text-muted fw-normal">(optional)</span></label>
                    <input
                        id="extractor-description"
                        v-model="form.description"
                        type="text"
                        class="form-control"
                        placeholder="What this extractor does"
                    />
                </div>
            </div>
        </fieldset>

        <!-- Endpoint + I/O -->
        <fieldset class="form-section">
            <legend class="form-section-title">Endpoint &amp; I/O</legend>

            <div class="row g-3">
                <div class="col-md-9">
                    <label for="extractor-url" class="form-label fw-bold">Endpoint URL</label>
                    <input
                        id="extractor-url"
                        v-model="form.url"
                        type="url"
                        class="form-control"
                        :class="{ 'is-invalid': errors.url }"
                        placeholder="https://my-extractor.example/api/extract"
                    />
                    <p class="field-hint">
                        <code>{{ textPlaceholder }}</code> may be used in the URL for services taking
                        the text as a query parameter, e.g. <code>…/api?text={{ textPlaceholder }}&amp;nel=true</code>.
                    </p>
                    <p v-if="errors.url" class="field-error">{{ errors.url }}</p>
                </div>

                <div class="col-md-3">
                    <label for="extractor-method" class="form-label fw-bold">Method</label>
                    <Select
                        id="extractor-method"
                        v-model="form.method"
                        :options="methodOptions"
                    />
                </div>

                <div class="col-md-4">
                    <label for="extractor-body-type" class="form-label fw-bold">Body type</label>
                    <Select
                        id="extractor-body-type"
                        v-model="form.bodyType"
                        :options="bodyTypeOptions"
                    />
                </div>
            </div>

            <div class="mt-3">
                <label class="form-label fw-bold mb-2">Headers <span class="text-muted fw-normal">(optional)</span></label>
                <div
                    v-for="(header, index) in form.headers"
                    :key="index"
                    class="header-row"
                >
                    <input
                        v-model="header.key"
                        type="text"
                        class="form-control"
                        placeholder="Authorization"
                        aria-label="Header name"
                    />
                    <input
                        v-model="header.value"
                        type="text"
                        class="form-control"
                        placeholder="Bearer ..."
                        aria-label="Header value"
                    />
                    <button
                        type="button"
                        class="header-remove-btn"
                        aria-label="Remove header"
                        @click="removeHeader(index)"
                    >✕</button>
                </div>
                <button type="button" class="add-row-button" @click="addHeader">+ Add header</button>
                <p class="field-hint">Secrets (API keys) are stored on the backend and never re-exposed.</p>
            </div>

            <div class="mt-3">
                <label for="extractor-body" class="form-label fw-bold">
                    Request body template
                    <span v-if="urlCarriesText" class="text-muted fw-normal">(optional, text is in the URL)</span>
                </label>
                <Textarea
                    id="extractor-body"
                    v-model="form.bodyTemplate"
                    :rows="5"
                    extraClass="code-textarea"
                    :class="{ 'is-invalid': errors.bodyTemplate }"
                    :placeholder="bodyTemplatePlaceholder"
                />
                <p class="field-hint">{{ bodyTemplateHint }} Use <code>{{ textPlaceholder }}</code> where the input text should be injected.</p>
                <p v-if="errors.bodyTemplate" class="field-error">{{ errors.bodyTemplate }}</p>
            </div>

            <div class="mt-3">
                <label for="extractor-timeout" class="form-label fw-bold">Timeout (seconds)</label>
                <input
                    id="extractor-timeout"
                    v-model.number="form.timeoutSeconds"
                    type="number"
                    min="1"
                    max="300"
                    class="form-control timeout-input"
                    :class="{ 'is-invalid': errors.timeoutSeconds }"
                />
                <p class="field-hint">Increase for slow LLM-based extractors (60+ recommended).</p>
                <p v-if="errors.timeoutSeconds" class="field-error">{{ errors.timeoutSeconds }}</p>
            </div>
        </fieldset>

        <!-- Output mapping -->
        <fieldset class="form-section">
            <legend class="form-section-title">Output mapping</legend>

            <div class="format-toggle mb-3">
                <label class="format-toggle-option">
                    <input v-model="form.responseFormat" type="radio" name="response-format" value="standard" />
                    <span>Standard TripleFlow contract</span>
                </label>
                <label class="format-toggle-option">
                    <input v-model="form.responseFormat" type="radio" name="response-format" value="custom" />
                    <span>Custom mapping</span>
                </label>
            </div>

            <p v-if="form.responseFormat === 'standard'" class="field-hint standard-contract mb-0">
                The endpoint must return:
                <code>{ "triples": [ { "subject": { "qid", "label" }, "predicate": { "pid", "label" }, "obj": { "qid", "label" } } ] }</code>
            </p>

            <div v-else>
                <p class="field-hint mb-3">
                    Dot-paths into the extractor response, telling the backend where to read each part
                    of a triple. Fallbacks separated by <code>|</code> are tried in order until one
                    yields a value, e.g. <code>owiki|oliteral</code>.
                </p>

                <div class="mb-3">
                    <label for="map-decode-json" class="form-label fw-bold">Embedded JSON path <span class="text-muted fw-normal">(optional)</span></label>
                    <input
                        id="map-decode-json"
                        v-model="form.mapping.decodeJsonPath"
                        type="text"
                        class="form-control"
                        placeholder="choices.0.message.content"
                    />
                    <p class="field-hint">
                        When the response nests the result as a JSON <em>string</em> (e.g. an LLM chat
                        completion), path to that string. The paths below then apply to the decoded document.
                    </p>
                </div>

                <div class="mb-3">
                    <label for="map-triples-path" class="form-label fw-bold">Triples array path</label>
                    <input
                        id="map-triples-path"
                        v-model="form.mapping.triplesPath"
                        type="text"
                        class="form-control"
                        :class="{ 'is-invalid': errors.triplesPath }"
                        placeholder="result.triples"
                    />
                    <p class="field-hint">
                        Supports numeric indices and a <code>*</code> wildcard that flattens lists,
                        e.g. <code>sentences.*.openie</code>.
                    </p>
                    <p v-if="errors.triplesPath" class="field-error">{{ errors.triplesPath }}</p>
                </div>

                <div
                    v-for="part in mappingParts"
                    :key="part.key"
                    class="row g-3 align-items-end mb-2"
                >
                    <div class="col-12 col-md-4">
                        <label :for="`map-${part.key}-id`" class="form-label fw-bold">{{ part.label }} — id path</label>
                        <input
                            :id="`map-${part.key}-id`"
                            v-model="form.mapping[part.key].id"
                            type="text"
                            class="form-control"
                            :class="{ 'is-invalid': errors[`${part.key}Id`] }"
                            :placeholder="part.idPlaceholder"
                        />
                        <p v-if="errors[`${part.key}Id`]" class="field-error">{{ errors[`${part.key}Id`] }}</p>
                    </div>
                    <div class="col-12 col-md-4">
                        <label :for="`map-${part.key}-label`" class="form-label fw-bold">{{ part.label }} — label path</label>
                        <input
                            :id="`map-${part.key}-label`"
                            v-model="form.mapping[part.key].label"
                            type="text"
                            class="form-control"
                            :placeholder="part.labelPlaceholder"
                        />
                    </div>
                </div>

                <div class="row g-3 mt-0">
                    <div class="col-12 col-md-6">
                        <label for="map-date" class="form-label fw-bold">Date path <span class="text-muted fw-normal">(optional)</span></label>
                        <input
                            id="map-date"
                            v-model="form.mapping.datePath"
                            type="text"
                            class="form-control"
                            placeholder="date"
                        />
                    </div>
                </div>
            </div>
        </fieldset>

        <!-- Knowledge base -->
        <fieldset class="form-section">
            <legend class="form-section-title">Knowledge base / QIDs</legend>
            <p class="field-hint mb-3">
                When the extractor returns QIDs/PIDs, they become clickable links to this base.
                Parts without a QID/PID stay unlinked.
            </p>

            <div class="row g-3">
                <div class="col-md-4">
                    <label for="kb-type" class="form-label fw-bold">Linking base</label>
                    <Select
                        id="kb-type"
                        v-model="form.kb.type"
                        :options="kbTypeOptions"
                    />
                </div>
                <div class="col-md-4">
                    <label for="kb-entity" class="form-label fw-bold">Entity id format</label>
                    <input
                        id="kb-entity"
                        v-model="form.kb.entityFormat"
                        type="text"
                        class="form-control"
                        placeholder="Q\d+"
                    />
                </div>
                <div class="col-md-4">
                    <label for="kb-property" class="form-label fw-bold">Property id format</label>
                    <input
                        id="kb-property"
                        v-model="form.kb.propertyFormat"
                        type="text"
                        class="form-control"
                        placeholder="P\d+"
                    />
                </div>

                <div v-if="form.kb.type === 'wikibase'" class="col-12">
                    <label for="kb-base-url" class="form-label fw-bold">Wikibase base URL</label>
                    <input
                        id="kb-base-url"
                        v-model="form.kb.baseUrl"
                        type="url"
                        class="form-control"
                        :class="{ 'is-invalid': errors.baseUrl }"
                        placeholder="https://my-wikibase.example/wiki/"
                    />
                    <p class="field-hint">
                        QIDs link to <code>&lt;base&gt;Item:Q…</code> and PIDs to <code>&lt;base&gt;Property:P…</code>.
                    </p>
                    <p v-if="errors.baseUrl" class="field-error">{{ errors.baseUrl }}</p>
                </div>

                <div v-if="form.kb.type === 'wikibase'" class="col-12">
                    <label for="kb-search-api" class="form-label fw-bold">Search API URL <span class="text-muted fw-normal">(optional)</span></label>
                    <input
                        id="kb-search-api"
                        v-model="form.kb.searchApiUrl"
                        type="url"
                        class="form-control"
                        :class="{ 'is-invalid': errors.searchApiUrl }"
                        placeholder="https://my-wikibase.example/w/api.php"
                    />
                    <p class="field-hint">
                        MediaWiki <code>api.php</code> used for entity autocomplete when editing triples.
                        Leave empty if this Wikibase has no search API — suggestions are simply disabled.
                        (Wikidata bases always use the public Wikidata search API.)
                    </p>
                    <p v-if="errors.searchApiUrl" class="field-error">{{ errors.searchApiUrl }}</p>
                </div>
            </div>
        </fieldset>

        <!-- Test panel -->
        <fieldset class="form-section">
            <legend class="form-section-title">Test before saving <span class="text-muted fw-normal">(optional)</span></legend>

            <label for="sample-text" class="form-label fw-bold">Sample text</label>
            <Textarea
                id="sample-text"
                v-model="sampleText"
                :rows="3"
                placeholder="Paste a short text to run the extractor against..."
            />

            <div class="mt-2">
                <Button
                    variant="outline-secondary"
                    :disabled="testing || !sampleText.trim()"
                    @click="onTest"
                >
                    {{ testing ? 'Testing…' : 'Test configuration' }}
                </Button>
            </div>

            <div v-if="testError" class="alert alert-danger mt-3 mb-0" role="alert">
                {{ testError }}
            </div>

            <div v-else-if="testResult" class="test-result mt-3">
                <p class="fw-bold mb-2">{{ testResult.length }} triple(s) returned</p>
                <ul v-if="testResult.length" class="test-result-list">
                    <li v-for="(triple, index) in testResult" :key="index">
                        <span class="triple-part">{{ partLabel(triple.subject) }}</span>
                        <span class="triple-arrow">—{{ partLabel(triple.predicate) }}→</span>
                        <span class="triple-part">{{ partLabel(triple.obj ?? triple.object) }}</span>
                    </li>
                </ul>
                <p v-else class="text-muted mb-0">No triples — check your mapping paths.</p>
            </div>
        </fieldset>

        <div v-if="createError" class="alert alert-danger" role="alert">
            {{ createError }}
        </div>

        <div class="d-flex gap-2">
            <Button variant="primary" type="submit" :disabled="submitting">
                {{ submitting ? 'Saving…' : 'Add extractor' }}
            </Button>
            <Button variant="outline-secondary" :disabled="submitting" @click="resetForm">
                Reset
            </Button>
        </div>
    </form>
</template>

<script setup>
/**
 * Form to register a custom extractor. Collects identity, endpoint/IO, output mapping and
 * knowledge-base settings, validates them, and emits the assembled config. Includes an
 * optional "test" action that runs the config against a sample text before saving.
 */
import { computed, reactive, ref } from 'vue'
import Button from '../atoms/Button.vue'
import Select from '../atoms/Select.vue'
import Textarea from '../atoms/Textarea.vue'

const props = defineProps({
    existingIds: {
        type: Array,
        default: () => [],
    },
    submitting: {
        type: Boolean,
        default: false,
    },
    createError: {
        type: String,
        default: '',
    },
    testing: {
        type: Boolean,
        default: false,
    },
    testError: {
        type: String,
        default: '',
    },
    testResult: {
        type: Array,
        default: null,
    },
})

const emit = defineEmits(['submit', 'test'])

const textPlaceholder = '{{text}}'

const methodOptions = [
    { value: 'POST', label: 'POST' },
]

const bodyTypeOptions = [
    { value: 'json', label: 'JSON' },
    { value: 'raw', label: 'Raw text' },
    { value: 'form', label: 'Form (urlencoded)' },
]

const BODY_TYPE_UI = {
    json: {
        hint: 'JSON body.',
        placeholder: '{ "text": "{{text}}" }',
    },
    raw: {
        hint: 'Sent as-is as the request body (text/plain unless you set a Content-Type header).',
        placeholder: '{{text}}',
    },
    form: {
        hint: 'Flat JSON object sent as form-urlencoded key/value pairs.',
        placeholder: '{ "extractors": "relations", "text": "{{text}}" }',
    },
}

const bodyTemplatePlaceholder = computed(() => BODY_TYPE_UI[form.bodyType].placeholder)
const bodyTemplateHint = computed(() => BODY_TYPE_UI[form.bodyType].hint)
const urlCarriesText = computed(() => form.url.includes(textPlaceholder))

const kbTypeOptions = [
    { value: 'wikidata', label: 'Wikidata' },
    { value: 'wikibase', label: 'Other Wikibase (custom URL)' },
]

const mappingParts = [
    { key: 'subject', label: 'Subject', idPlaceholder: 'subject.qid', labelPlaceholder: 'subject.label' },
    { key: 'predicate', label: 'Predicate', idPlaceholder: 'predicate.pid', labelPlaceholder: 'predicate.label' },
    { key: 'object', label: 'Object', idPlaceholder: 'obj.qid', labelPlaceholder: 'obj.label' },
]

/**
 * Mapping used when the endpoint follows the standard TripleFlow response contract:
 * `{ "triples": [{ "subject": {"qid","label"}, "predicate": {"pid","label"},
 * "obj": {"qid","label"} }] }`. Same shape as `form.mapping`
 * so buildConfig can consume either one.
 */
const STANDARD_MAPPING = {
    triplesPath: 'triples',
    subject: { id: 'subject.qid', label: 'subject.label' },
    predicate: { id: 'predicate.pid', label: 'predicate.label' },
    object: { id: 'obj.qid', label: 'obj.label' },
}

/** Returns the default, empty-ish form state pre-filled with common mapping hints. */
function createDefaultForm() {
    return {
        id: '',
        label: '',
        description: '',
        url: '',
        method: 'POST',
        headers: [],
        bodyType: 'json',
        bodyTemplate: '{\n  "text": "{{text}}"\n}',
        responseFormat: 'standard',
        timeoutSeconds: 30,
        mapping: {
            decodeJsonPath: '',
            triplesPath: 'result.triples',
            subject: { id: 'subject.qid', label: 'subject.label' },
            predicate: { id: 'predicate.pid', label: 'predicate.label' },
            object: { id: 'obj.qid', label: 'obj.label' },
            datePath: '',
        },
        kb: {
            type: 'wikidata',
            baseUrl: '',
            searchApiUrl: '',
            entityFormat: 'Q\\d+',
            propertyFormat: 'P\\d+',
        },
    }
}

const form = reactive(createDefaultForm())
const sampleText = ref('')
const errors = reactive({})

function addHeader() {
    form.headers.push({ key: '', value: '' })
}

function removeHeader(index) {
    form.headers.splice(index, 1)
}

/** Renders a triple part as a readable "label (id)" string for the test preview. */
function partLabel(part) {
    if (!part) return '∅'
    if (typeof part === 'string') return part
    const id = part.id || part.qid || part.pid || ''
    const label = part.label || ''
    if (label && id) return `${label} (${id})`
    return label || id || '∅'
}

/** Converts the headers rows into a plain object, dropping rows with an empty key. */
function buildHeadersObject() {
    return form.headers.reduce((accumulator, header) => {
        const key = header.key.trim()
        if (key) {
            accumulator[key] = header.value
        }
        return accumulator
    }, {})
}

/** Clears all field-level errors. */
function clearErrors() {
    Object.keys(errors).forEach((key) => delete errors[key])
}

/**
 * Validates the form. Populates `errors` and returns the parsed body template
 * (or null when invalid) so the caller does not parse it twice.
 * @returns {{ valid: boolean, parsedBody: object|null }}
 */
function validate() {
    clearErrors()

    const id = form.id.trim()
    if (!id) {
        errors.id = 'Slug is required.'
    } else if (!/^[a-z0-9][a-z0-9_-]*$/.test(id)) {
        errors.id = 'Use lowercase letters, digits, hyphens or underscores.'
    } else if (props.existingIds.includes(id)) {
        errors.id = 'An extractor with this slug already exists.'
    }

    if (!form.label.trim()) {
        errors.label = 'Display name is required.'
    }

    if (!form.url.trim()) {
        errors.url = 'Endpoint URL is required.'
    } else {
        try {
            new URL(form.url.trim())
        } catch {
            errors.url = 'Enter a valid absolute URL.'
        }
    }

    let parsedBody = null
    const rawBody = form.bodyTemplate.trim()
    if (!rawBody) {
        if (!urlCarriesText.value) {
            errors.bodyTemplate = `Request body template is required (or put ${textPlaceholder} in the URL).`
        }
    } else if (!rawBody.includes(textPlaceholder) && !urlCarriesText.value) {
        errors.bodyTemplate = `The template must contain the ${textPlaceholder} placeholder.`
    } else if (form.bodyType === 'raw') {
        parsedBody = rawBody
    } else {
        try {
            parsedBody = JSON.parse(rawBody)
        } catch {
            errors.bodyTemplate = 'The body template must be valid JSON.'
        }
        if (
            parsedBody !== null
            && (typeof parsedBody !== 'object' || Array.isArray(parsedBody))
        ) {
            errors.bodyTemplate = form.bodyType === 'form'
                ? 'The form body template must be a JSON object of key/value pairs.'
                : 'The body template must be a JSON object.'
            parsedBody = null
        }
    }

    if (form.responseFormat === 'custom') {
        if (!form.mapping.triplesPath.trim()) {
            errors.triplesPath = 'Triples array path is required.'
        }
        if (!form.mapping.subject.id.trim()) {
            errors.subjectId = 'Subject id path is required.'
        }
        if (!form.mapping.predicate.id.trim()) {
            errors.predicateId = 'Predicate id path is required.'
        }
        if (!form.mapping.object.id.trim()) {
            errors.objectId = 'Object id path is required.'
        }
    }

    if (!Number.isFinite(form.timeoutSeconds) || form.timeoutSeconds < 1 || form.timeoutSeconds > 300) {
        errors.timeoutSeconds = 'Enter a timeout between 1 and 300 seconds.'
    }

    if (form.kb.type === 'wikibase') {
        const searchApiUrl = form.kb.searchApiUrl.trim()
        if (searchApiUrl) {
            try {
                new URL(searchApiUrl)
            } catch {
                errors.searchApiUrl = 'Enter a valid absolute URL.'
            }
        }

        const baseUrl = form.kb.baseUrl.trim()
        if (!baseUrl) {
            errors.baseUrl = 'Base URL is required for a custom Wikibase.'
        } else {
            try {
                new URL(baseUrl)
            } catch {
                errors.baseUrl = 'Enter a valid absolute URL.'
            }
        }
    }

    return { valid: Object.keys(errors).length === 0, parsedBody }
}

/** Assembles the extractor config object from the current form state. */
function buildConfig(parsedBody) {
    const headers = buildHeadersObject()
    // "Standard" is only a pre-baked mapping: the backend always receives a full
    // output_mapping and does not need to know which mode produced it.
    const mapping = form.responseFormat === 'standard' ? STANDARD_MAPPING : form.mapping

    return {
        id: form.id.trim(),
        label: form.label.trim(),
        description: form.description.trim(),
        endpoint: {
            url: form.url.trim(),
            method: form.method,
            ...(Object.keys(headers).length > 0 && { headers }),
            body_type: form.bodyType,
            ...(parsedBody !== null && { body_template: parsedBody }),
            timeout_seconds: form.timeoutSeconds,
        },
        output_mapping: {
            ...(form.responseFormat === 'custom' && form.mapping.decodeJsonPath.trim()
                && { decode_json_path: form.mapping.decodeJsonPath.trim() }),
            triples_path: mapping.triplesPath.trim(),
            subject: { id: mapping.subject.id.trim(), label: mapping.subject.label.trim() },
            predicate: { id: mapping.predicate.id.trim(), label: mapping.predicate.label.trim() },
            object: { id: mapping.object.id.trim(), label: mapping.object.label.trim() },
            ...(form.responseFormat === 'custom' && form.mapping.datePath.trim()
                && { date: form.mapping.datePath.trim() }),
        },
        knowledge_base: {
            type: form.kb.type,
            ...(form.kb.type === 'wikibase' && { base_url: form.kb.baseUrl.trim() }),
            ...(form.kb.type === 'wikibase' && form.kb.searchApiUrl.trim()
                && { search_api_url: form.kb.searchApiUrl.trim() }),
            entity_id_format: form.kb.entityFormat.trim(),
            property_id_format: form.kb.propertyFormat.trim(),
        },
    }
}

function onSubmit() {
    const { valid, parsedBody } = validate()
    if (!valid) return
    emit('submit', buildConfig(parsedBody))
}

function onTest() {
    const { valid, parsedBody } = validate()
    if (!valid) return
    emit('test', { config: buildConfig(parsedBody), sampleText: sampleText.value.trim() })
}

function resetForm() {
    Object.assign(form, createDefaultForm())
    sampleText.value = ''
    clearErrors()
}

defineExpose({ resetForm })
</script>

<style scoped>
.extractor-form {
    --ods-orange-100: #ff7900;
    --ods-gray-300: #ddd;
    --ods-gray-500: #999;
    --ods-gray-700: #595959;
}

.form-section {
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.5rem;
    padding: 1.25rem;
    margin-bottom: 1.5rem;
}

.form-section-title {
    float: none;
    width: auto;
    font-size: 1rem;
    font-weight: 700;
    color: var(--ods-orange-100);
    padding: 0 0.5rem;
    margin-left: -0.5rem;
}

.field-hint {
    font-size: 0.8rem;
    color: var(--ods-gray-700);
    margin: 0.35rem 0 0;
}

.field-hint code {
    color: var(--ods-orange-100);
}

.field-error {
    font-size: 0.8rem;
    font-weight: 600;
    color: #cd3c14;
    margin: 0.35rem 0 0;
}

.format-toggle {
    display: flex;
    flex-wrap: wrap;
    gap: 1.25rem;
}

.format-toggle-option {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-weight: 600;
    cursor: pointer;
}

.format-toggle-option input {
    accent-color: var(--ods-orange-100);
}

.standard-contract code {
    display: block;
    margin-top: 0.35rem;
    padding: 0.5rem 0.75rem;
    background: #fafafa;
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.4rem;
    overflow-x: auto;
}

.timeout-input {
    max-width: 8rem;
}

.header-row {
    display: grid;
    grid-template-columns: 1fr 1.5fr auto;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}

.header-remove-btn {
    border: none;
    background: transparent;
    color: var(--ods-gray-500);
    cursor: pointer;
    padding: 0 0.5rem;
    border-radius: 0.2rem;
    transition: color 0.15s;
}

.header-remove-btn:hover {
    color: #cd3c14;
}

.add-row-button {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.3rem 0.85rem;
    border: 0.1rem dashed var(--ods-gray-300);
    border-radius: 0.4rem;
    background: transparent;
    color: var(--ods-gray-700);
    font-size: 0.85rem;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
}

.add-row-button:hover {
    border-color: var(--ods-orange-100);
    color: var(--ods-orange-100);
}

.code-textarea {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.85rem;
}

.test-result {
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.5rem;
    padding: 1rem;
    background: #fafafa;
}

.test-result-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
}

.test-result-list li {
    font-size: 0.85rem;
}

.triple-part {
    font-weight: 600;
}

.triple-arrow {
    color: var(--ods-orange-100);
    margin: 0 0.4rem;
}
</style>
