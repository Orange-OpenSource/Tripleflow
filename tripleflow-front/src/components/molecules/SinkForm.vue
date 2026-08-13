<template>
    <form class="sink-form" @submit.prevent="onSubmit">
        <!-- Identity -->
        <fieldset class="form-section">
            <legend class="form-section-title">Identity</legend>

            <div class="row g-3">
                <div class="col-md-6">
                    <label for="sink-id" class="form-label fw-bold">Slug</label>
                    <input
                        id="sink-id"
                        v-model="form.id"
                        type="text"
                        class="form-control"
                        :class="{ 'is-invalid': errors.id }"
                        placeholder="my-triplestore"
                        autocomplete="off"
                    />
                    <p class="field-hint">Lowercase technical id used in the publish URL.</p>
                    <p v-if="errors.id" class="field-error">{{ errors.id }}</p>
                </div>

                <div class="col-md-6">
                    <label for="sink-label" class="form-label fw-bold">Display name</label>
                    <input
                        id="sink-label"
                        v-model="form.label"
                        type="text"
                        class="form-control"
                        :class="{ 'is-invalid': errors.label }"
                        placeholder="My Triplestore"
                    />
                    <p v-if="errors.label" class="field-error">{{ errors.label }}</p>
                </div>

                <div class="col-12">
                    <label for="sink-description" class="form-label fw-bold">
                        Description <span class="text-muted fw-normal">(optional)</span>
                    </label>
                    <input
                        id="sink-description"
                        v-model="form.description"
                        type="text"
                        class="form-control"
                        placeholder="Where these triples end up"
                    />
                </div>
            </div>
        </fieldset>

        <!-- How the target is written to -->
        <fieldset class="form-section">
            <legend class="form-section-title">How this graph is written to</legend>

            <div class="row g-3">
                <div class="col-12">
                    <Select id="sink-type" v-model="form.type" :options="targetTypeOptions" />
                    <p class="field-hint">{{ targetTypeHint }}</p>
                </div>
            </div>
        </fieldset>

        <!-- Endpoint -->
        <fieldset class="form-section">
            <legend class="form-section-title">
                {{ isHttp ? 'API endpoint' : 'SPARQL endpoint' }}
            </legend>

            <div class="row g-3">
                <div v-if="!isHttp" class="col-12">
                    <label for="sink-url" class="form-label fw-bold">Update URL</label>
                    <input
                        id="sink-url"
                        v-model="form.updateUrl"
                        type="url"
                        class="form-control"
                        :class="{ 'is-invalid': errors.updateUrl }"
                        placeholder="https://fuseki.example/dataset/update"
                    />
                    <p class="field-hint">
                        SPARQL 1.1 Update endpoint. TripleFlow sends an
                        <code>INSERT DATA</code> to it — usually the <code>/update</code> path, not <code>/query</code>.
                    </p>
                    <p v-if="errors.updateUrl" class="field-error">{{ errors.updateUrl }}</p>
                </div>

                <div v-if="isHttp" class="col-12">
                    <label for="sink-api-url" class="form-label fw-bold">URL called for each triple</label>
                    <input
                        id="sink-api-url"
                        v-model="form.http.url"
                        type="url"
                        class="form-control"
                        :class="{ 'is-invalid': errors.httpUrl }"
                        placeholder="https://kg.example.org/w/api.php"
                    />
                    <p class="field-hint">One call per published triple.</p>
                    <p v-if="errors.httpUrl" class="field-error">{{ errors.httpUrl }}</p>
                </div>

                <div v-if="!isHttp" class="col-md-8">
                    <label for="sink-body-format" class="form-label fw-bold">Request body</label>
                    <Select
                        id="sink-body-format"
                        v-model="form.bodyFormat"
                        :options="bodyFormatOptions"
                    />
                    <p class="field-hint">{{ bodyFormatHint }}</p>
                </div>

                <div class="col-md-4">
                    <label for="sink-timeout" class="form-label fw-bold">Timeout (s)</label>
                    <input
                        id="sink-timeout"
                        v-model.number="form.timeoutSeconds"
                        type="number"
                        min="1"
                        max="300"
                        class="form-control"
                        :class="{ 'is-invalid': errors.timeoutSeconds }"
                    />
                    <p class="field-hint">Raise it if you publish large batches.</p>
                    <p v-if="errors.timeoutSeconds" class="field-error">{{ errors.timeoutSeconds }}</p>
                </div>

                <div class="col-12">
                    <label class="form-label fw-bold mb-2">
                        Headers <span class="text-muted fw-normal">(optional)</span>
                    </label>
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
                    <p class="field-hint">
                        Sent with every request, whatever the authentication method below — a token, a tenant
                        header, an overridden <code>Content-Type</code>. Values are stored on the backend and
                        never re-exposed.
                    </p>
                    <p v-if="errors.headers" class="field-error">{{ errors.headers }}</p>
                </div>

                <div v-if="!isHttp" class="col-12">
                    <label for="sink-graph" class="form-label fw-bold">
                        Named graph URI <span class="text-muted fw-normal">(optional)</span>
                    </label>
                    <input
                        id="sink-graph"
                        v-model="form.graphUri"
                        type="url"
                        class="form-control"
                        :class="{ 'is-invalid': errors.graphUri }"
                        placeholder="https://example.org/graph/tripleflow"
                    />
                    <p class="field-hint">
                        Triples are inserted into this graph. Leave empty to write to the default graph.
                    </p>
                    <p v-if="errors.graphUri" class="field-error">{{ errors.graphUri }}</p>
                </div>
            </div>
        </fieldset>

        <!-- Auth -->
        <fieldset class="form-section">
            <legend class="form-section-title">Authentication</legend>

            <div class="row g-3">
                <div class="col-md-4">
                    <label for="sink-auth-type" class="form-label fw-bold">Method</label>
                    <Select
                        id="sink-auth-type"
                        v-model="form.auth.type"
                        :options="authTypeOptions"
                    />
                </div>
            </div>

            <div v-if="form.auth.type === 'basic'" class="row g-3 mt-0">
                <div class="col-md-6">
                    <label for="sink-username" class="form-label fw-bold">Username</label>
                    <input
                        id="sink-username"
                        v-model="form.auth.username"
                        type="text"
                        class="form-control"
                        :class="{ 'is-invalid': errors.username }"
                        autocomplete="off"
                    />
                    <p v-if="errors.username" class="field-error">{{ errors.username }}</p>
                </div>
                <div class="col-md-6">
                    <label for="sink-password" class="form-label fw-bold">Password</label>
                    <input
                        id="sink-password"
                        v-model="form.auth.password"
                        type="password"
                        class="form-control"
                        :class="{ 'is-invalid': errors.password }"
                        autocomplete="new-password"
                    />
                    <p v-if="errors.password" class="field-error">{{ errors.password }}</p>
                </div>
            </div>

            <p class="field-hint mt-2">
                Credentials are stored on the backend and never re-exposed — the browser never sees them,
                and it is the backend that reaches your endpoint. For a bearer token or an API key, add an
                <strong>Authorization</strong> header above instead.
            </p>
        </fieldset>

        <!-- Namespaces -->
        <fieldset class="form-section">
            <legend class="form-section-title">Identifier namespaces</legend>
            <p class="field-hint mb-3">
                How a triple's QIDs/PIDs become IRIs in the target graph. Defaults target public Wikidata;
                point them at your own base if you publish to an internal Wikibase.
            </p>

            <div class="row g-3">
                <div class="col-md-6">
                    <label for="sink-item-base" class="form-label fw-bold">Item base URI</label>
                    <input
                        id="sink-item-base"
                        v-model="form.namespaces.itemBaseUri"
                        type="url"
                        class="form-control"
                        :class="{ 'is-invalid': errors.itemBaseUri }"
                        placeholder="http://www.wikidata.org/entity/"
                    />
                    <p class="field-hint">Q42 → <code>{{ form.namespaces.itemBaseUri || '…' }}Q42</code></p>
                    <p v-if="errors.itemBaseUri" class="field-error">{{ errors.itemBaseUri }}</p>
                </div>
                <div class="col-md-6">
                    <label for="sink-property-base" class="form-label fw-bold">Property base URI</label>
                    <input
                        id="sink-property-base"
                        v-model="form.namespaces.propertyBaseUri"
                        type="url"
                        class="form-control"
                        :class="{ 'is-invalid': errors.propertyBaseUri }"
                        placeholder="http://www.wikidata.org/prop/direct/"
                    />
                    <p class="field-hint">P31 → <code>{{ form.namespaces.propertyBaseUri || '…' }}P31</code></p>
                    <p v-if="errors.propertyBaseUri" class="field-error">{{ errors.propertyBaseUri }}</p>
                </div>
            </div>
        </fieldset>

        <!-- Entity anchoring -->
        <fieldset class="form-section">
            <legend class="form-section-title">Entity anchoring</legend>
            <p class="field-hint mb-3">
                Where a published identifier can be <em>browsed</em>. Once a triple has been pushed here, its
                QIDs/PIDs link to this base on the Validation page, so a reviewer can check what landed in the
                knowledge graph. This is separate from the base URIs above: a Wikibase writes
                <code>…/entity/Q42</code> into the graph but serves the page at <code>…/wiki/Item:Q42</code>.
            </p>

            <div class="row g-3">
                <div class="col-md-5">
                    <label for="sink-kb-type" class="form-label fw-bold">Browsable base</label>
                    <Select
                        id="sink-kb-type"
                        v-model="form.knowledgeBase.type"
                        :options="kbTypeOptions"
                    />
                </div>

                <div v-if="form.knowledgeBase.type === 'wikibase'" class="col-md-7">
                    <label for="sink-kb-base-url" class="form-label fw-bold">Wiki base URL</label>
                    <input
                        id="sink-kb-base-url"
                        v-model="form.knowledgeBase.baseUrl"
                        type="url"
                        class="form-control"
                        :class="{ 'is-invalid': errors.kbBaseUrl }"
                        placeholder="https://my-wikibase.example/wiki/"
                    />
                    <p class="field-hint">
                        Q42 → <code>{{ kbSampleLink || '…Item:Q42' }}</code>
                    </p>
                    <p v-if="errors.kbBaseUrl" class="field-error">{{ errors.kbBaseUrl }}</p>
                </div>
            </div>
        </fieldset>

        <!-- HTTP request written by the user -->
        <fieldset v-if="isHttp" class="form-section">
            <legend class="form-section-title">The call sent for each triple</legend>

            <p class="field-hint">
                Write the request your API expects. TripleFlow fills the
                <code>{{ placeholderChip('…') }}</code> slots for every published triple and sends it as-is —
                it knows nothing about the API on the other end.
            </p>

            <div class="row g-3 mt-0">
                <div class="col-md-6">
                    <label for="sink-http-preset" class="form-label fw-bold">Start from an example</label>
                    <Select id="sink-http-preset" v-model="selectedHttpPreset" :options="httpPresetOptions" />
                </div>
                <div class="col-md-3">
                    <label for="sink-http-method" class="form-label fw-bold">Method</label>
                    <Select id="sink-http-method" v-model="form.http.method" :options="httpMethodOptions" />
                </div>
                <div class="col-md-3">
                    <label for="sink-http-body-type" class="form-label fw-bold">Body sent as</label>
                    <Select id="sink-http-body-type" v-model="form.http.bodyType" :options="httpBodyTypeOptions" />
                </div>
            </div>

            <div class="mt-3">
                <label for="sink-http-body" class="form-label fw-bold">Request body</label>
                <Textarea
                    id="sink-http-body"
                    v-model="form.http.bodyTemplate"
                    :rows="12"
                    :extraClass="errors.httpBody ? 'is-invalid' : ''"
                />
                <p class="field-hint">
                    A JSON object of fields, unless the body type is <code>raw</code>. Main slots:
                    <code v-for="name in mainPlaceholders" :key="name" class="placeholder-chip">{{ placeholderChip(name) }}</code>
                </p>
                <details class="placeholder-details">
                    <summary>All available slots</summary>
                    <ul class="placeholder-list">
                        <li v-for="group in httpPlaceholderGroups" :key="group.title">
                            <span class="placeholder-group-title">{{ group.title }}</span>
                            <code v-for="name in group.names" :key="name" class="placeholder-chip">{{ placeholderChip(name) }}</code>
                        </li>
                    </ul>
                    <p class="field-hint">
                        Put a <code>_json</code> slot wherever a value lands <em>inside</em> a quoted JSON
                        fragment — a label containing a quote would otherwise break it.
                    </p>
                </details>
                <p v-if="errors.httpBody" class="field-error">{{ errors.httpBody }}</p>
            </div>

            <div class="mt-3">
                <label for="sink-error-path" class="form-label fw-bold">
                    Where an error appears in the response
                </label>
                <input
                    id="sink-error-path"
                    v-model="form.http.errorPath"
                    type="text"
                    class="form-control"
                    placeholder="error.info"
                />
                <p class="field-hint">
                    Dot path, e.g. <code>error.info</code>. Many APIs — MediaWiki and Wikibase among them —
                    answer <code>200 OK</code> and put the problem in the body.
                    <strong>Leave this empty and a rejected write is counted as published.</strong>
                </p>
            </div>
        </fieldset>

        <!-- Prepare chain -->
        <fieldset v-if="isHttp" class="form-section">
            <legend class="form-section-title">
                Before publishing <span class="text-muted fw-normal">(optional)</span>
            </legend>

            <p class="field-hint">
                Calls made once before the triples, each able to keep a value from its response for the
                slots above. This is how a target obtains a CSRF token, or logs in — cookies are kept
                across the steps and the writes that follow.
            </p>

            <div v-for="(step, index) in form.http.prepare" :key="index" class="prepare-step">
                <div class="row g-2">
                    <div class="col-md-4">
                        <input v-model="step.name" type="text" class="form-control" placeholder="Step name" />
                    </div>
                    <div class="col-md-2">
                        <Select v-model="step.method" :options="prepareMethodOptions" />
                    </div>
                    <div class="col-md-6">
                        <input v-model="step.url" type="url" class="form-control" placeholder="https://…/api.php?action=query&meta=tokens&type=csrf&format=json" />
                    </div>
                    <div v-if="step.method === 'POST'" class="col-12">
                        <Textarea
                            v-model="step.bodyTemplate"
                            :rows="4"
                            placeholder='Body as JSON fields, e.g. {"action": "login", "lgname": "…", "lgpassword": "…", "lgtoken": "{{logintoken}}", "format": "json"}'
                        />
                        <p class="field-hint">
                            Sent as form fields. May use the slots captured by the steps above it.
                        </p>
                    </div>
                    <div class="col-md-4">
                        <input v-model="step.captureName" type="text" class="form-control" placeholder="Slot name, e.g. token" />
                    </div>
                    <div class="col-md-6">
                        <input v-model="step.capturePath" type="text" class="form-control" placeholder="Path, e.g. query.tokens.csrftoken" />
                    </div>
                    <div class="col-md-2">
                        <button type="button" class="btn btn-sm btn-outline-secondary w-100" @click="removePrepareStep(index)">
                            Remove
                        </button>
                    </div>
                </div>
            </div>

            <button type="button" class="btn btn-sm btn-outline-secondary mt-2" @click="addPrepareStep">
                + Add a step
            </button>
            <p v-if="errors.prepare" class="field-error">{{ errors.prepare }}</p>
        </fieldset>

        <!-- Write shape -->
        <fieldset v-if="!isHttp" class="form-section">
            <legend class="form-section-title">How triples are written</legend>

            <p class="field-hint">
                By default each validated triple is written as one plain assertion:
                <code>&lt;subject&gt; &lt;predicate&gt; &lt;object&gt;</code>. That is enough for most graphs.
            </p>

            <label class="template-toggle">
                <input v-model="form.useTemplate" type="checkbox" />
                My graph expects another shape (write the SPARQL myself)
            </label>

            <template v-if="form.useTemplate">
                <div class="row g-3 mt-0">
                    <div class="col-md-6">
                        <label for="sink-preset" class="form-label fw-bold">Start from an example</label>
                        <Select
                            id="sink-preset"
                            v-model="selectedPreset"
                            :options="presetOptions"
                        />
                    </div>
                </div>

                <div class="mt-3">
                    <label for="sink-template" class="form-label fw-bold">SPARQL sent for each triple</label>
                    <Textarea
                        id="sink-template"
                        v-model="form.updateTemplate"
                        :rows="12"
                        :extraClass="errors.updateTemplate ? 'is-invalid' : ''"
                    />
                    <p class="field-hint">
                        The <code>{{ placeholderChip('…') }}</code> slots are filled in for every published triple. Main ones:
                        <code v-for="name in mainPlaceholders" :key="name" class="placeholder-chip">{{ placeholderChip(name) }}</code>
                    </p>
                    <details class="placeholder-details">
                        <summary>All available slots</summary>
                        <ul class="placeholder-list">
                            <li v-for="group in placeholderGroups" :key="group.title">
                                <span class="placeholder-group-title">{{ group.title }}</span>
                                <code v-for="name in group.names" :key="name" class="placeholder-chip">{{ placeholderChip(name) }}</code>
                            </li>
                        </ul>
                        <p class="field-hint">
                            The <code>_iri</code> ones are full IRIs — wrap them in <code>&lt;…&gt;</code>.
                            Everything else goes inside <code>"…"</code> quotes.
                        </p>
                    </details>
                    <p v-if="errors.updateTemplate" class="field-error">{{ errors.updateTemplate }}</p>
                    <p class="template-warning">
                        Check the result with <strong>Preview SPARQL</strong> on the Validation page before
                        publishing for real.
                    </p>
                </div>
            </template>
        </fieldset>

        <div v-if="createError" class="alert alert-danger" role="alert">
            {{ createError }}
        </div>

        <div class="d-flex gap-2">
            <Button variant="primary" type="submit" :disabled="submitting">
                {{ submitting ? 'Saving…' : 'Add target' }}
            </Button>
            <Button variant="outline-secondary" :disabled="submitting" @click="resetForm">
                Reset
            </Button>
        </div>
    </form>
</template>

<script setup>
/**
 * Form to register a SPARQL UPDATE publication target. The user describes the call the
 * backend will make — URL, request body format, headers, timeout, credentials — plus how
 * identifiers are written as IRIs and where they can be browsed once published. Validates
 * it all and emits the assembled config.
 */
import { computed, reactive, ref, watch } from 'vue'
import Button from '../atoms/Button.vue'
import Select from '../atoms/Select.vue'
import Textarea from '../atoms/Textarea.vue'
import { buildWikibaseLink } from '../../composables/entityLinks.js'

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
})

const emit = defineEmits(['submit'])

const SLUG_RE = /^[a-z0-9][a-z0-9_-]*$/

// RFC 7230 token characters, same rule as the backend's HEADER_NAME_RE.
const HEADER_NAME_RE = /^[A-Za-z0-9!#$%&'*+.^_`|~-]+$/

// Token auth is not a method here: it is a header, and headers are configured on
// the endpoint so they can be combined with Basic rather than replace it.
const authTypeOptions = [
    { value: 'none', label: 'None' },
    { value: 'basic', label: 'HTTP Basic' },
]

/** The two ways SPARQL 1.1 Protocol lets an update travel; stores differ on what they accept. */
const BODY_FORMATS = {
    'sparql-update': {
        label: 'SPARQL update (application/sparql-update)',
        hint: 'The update is the whole request body. Works with Fuseki, GraphDB, Blazegraph.',
    },
    'form-urlencoded': {
        label: 'Form-encoded (update=…)',
        hint: 'The update is sent as an `update` form parameter. Required by stores that reject a raw body, such as Virtuoso.',
    },
}

const bodyFormatOptions = Object.entries(BODY_FORMATS).map(([value, format]) => ({
    value,
    label: format.label,
}))

const kbTypeOptions = [
    { value: 'none', label: 'None — do not link published ids' },
    { value: 'wikidata', label: 'Public Wikidata' },
    { value: 'wikibase', label: 'Wikibase instance' },
]

/** Placeholder names the backend substitutes, grouped for the form's reference list. */
const placeholderGroups = [
    { title: 'IRIs', names: ['subject_iri', 'predicate_iri', 'object_iri', 'graph'] },
    { title: 'Identifiers', names: ['subject_id', 'predicate_id', 'object_id'] },
    { title: 'Labels', names: ['subject_label', 'predicate_label', 'object_label'] },
    { title: 'Provenance', names: ['triple_id', 'reviewer', 'source_file', 'extractors', 'now', 'uuid'] },
]

const KNOWN_PLACEHOLDERS = placeholderGroups.flatMap((group) => group.names)

const mainPlaceholders = ['subject_iri', 'predicate_iri', 'object_iri', 'subject_label', 'object_label']

/**
 * Renders a placeholder name as it is typed in a template. Built here rather than
 * inline in the markup: Vue's own interpolation uses the same braces and would
 * close on the wrong ones.
 */
function placeholderChip(name) {
    return `{${'{'}${name}${'}'}}`
}

/**
 * Ready-to-use starting points for the template textarea. PREFIX lines sit at the
 * top of the same text; buildConfig splits them out so they are sent once per
 * request instead of once per triple.
 */
const PRESETS = {
    labels: {
        label: 'Triple + labels',
        text: `PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT DATA {
  GRAPH <{{graph}}> {
    <{{subject_iri}}> <{{predicate_iri}}> <{{object_iri}}> .
    <{{subject_iri}}> rdfs:label "{{subject_label}}" .
    <{{object_iri}}> rdfs:label "{{object_label}}" .
  }
}`,
    },
    wikibase: {
        label: 'Wikibase statement model',
        text: `PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX p: <https://your-wikibase.example/prop/>
PREFIX ps: <https://your-wikibase.example/prop/statement/>
PREFIX s: <https://your-wikibase.example/entity/statement/>

INSERT DATA {
  GRAPH <{{graph}}> {
    <{{subject_iri}}> <{{predicate_iri}}> <{{object_iri}}> .
    <{{subject_iri}}> p:{{predicate_id}} s:{{subject_id}}-{{uuid}} .
    s:{{subject_id}}-{{uuid}} a wikibase:Statement ;
        wikibase:rank wikibase:NormalRank ;
        ps:{{predicate_id}} <{{object_iri}}> .
  }
}`,
    },
    replace: {
        label: 'Replace the old value (single-value property)',
        text: `DELETE { GRAPH <{{graph}}> { <{{subject_iri}}> <{{predicate_iri}}> ?old } }
INSERT { GRAPH <{{graph}}> { <{{subject_iri}}> <{{predicate_iri}}> <{{object_iri}}> } }
WHERE  { OPTIONAL { GRAPH <{{graph}}> { <{{subject_iri}}> <{{predicate_iri}}> ?old } } }`,
    },
}

const presetOptions = Object.entries(PRESETS).map(([value, preset]) => ({ value, label: preset.label }))

const targetTypeOptions = [
    { value: 'sparql', label: 'A SPARQL 1.1 Update endpoint (triplestore)' },
    { value: 'http', label: 'Its own HTTP API (Wikibase, in-house service…)' },
]

const TARGET_TYPE_HINTS = {
    sparql: 'One SPARQL update sent for the whole batch. Right for Fuseki, GraphDB, Virtuoso…',
    http: 'One HTTP call per triple, described below. Needed for a knowledge base that is not '
        + 'written through SPARQL — a Wikibase, whose SPARQL endpoint is a read-only mirror, is '
        + 'written through its own API.',
}

const httpMethodOptions = ['POST', 'PUT', 'PATCH'].map((value) => ({ value, label: value }))
const prepareMethodOptions = ['GET', 'POST'].map((value) => ({ value, label: value }))
const httpBodyTypeOptions = [
    { value: 'form', label: 'form fields' },
    { value: 'json', label: 'JSON' },
    { value: 'raw', label: 'raw text' },
]

// Slots an HTTP target can use, on top of the SPARQL ones.
const httpPlaceholderGroups = [
    ...placeholderGroups,
    { title: 'Numeric ids', names: ['subject_numeric_id', 'object_numeric_id'] },
    {
        title: 'JSON-safe',
        names: [
            'subject_label_json', 'predicate_label_json', 'object_label_json',
            'source_file_json', 'reviewer_json',
        ],
    },
]
const KNOWN_HTTP_PLACEHOLDERS = httpPlaceholderGroups.flatMap((group) => group.names)

/**
 * Starting points for the HTTP body. The Wikibase one is a worked example of the
 * general mechanism, not special-cased anywhere in the code: it is only what a
 * user would have typed to drive that API.
 */
const HTTP_PRESETS = {
    wikibase: {
        label: 'Wikibase — add a statement (wbcreateclaim)',
        method: 'POST',
        bodyType: 'form',
        errorPath: 'error.info',
        prepare: [{
            name: 'CSRF token',
            method: 'GET',
            url: 'https://your-wikibase.example/w/api.php?action=query&meta=tokens&type=csrf&format=json',
            captureName: 'token',
            capturePath: 'query.tokens.csrftoken',
        }],
        body: `{
  "action": "wbcreateclaim",
  "format": "json",
  "entity": "{{subject_id}}",
  "property": "{{predicate_id}}",
  "snaktype": "value",
  "value": "{\\"entity-type\\":\\"item\\",\\"numeric-id\\":{{object_numeric_id}}}",
  "summary": "TripleFlow — validated by {{reviewer_json}} ({{source_file_json}})",
  "token": "{{token}}"
}`,
    },
    rest: {
        label: 'Plain JSON REST endpoint',
        method: 'POST',
        bodyType: 'json',
        errorPath: '',
        prepare: [],
        body: `{
  "subject": "{{subject_id}}",
  "predicate": "{{predicate_id}}",
  "object": "{{object_id}}",
  "subject_label": "{{subject_label}}",
  "object_label": "{{object_label}}",
  "reviewer": "{{reviewer}}",
  "source": "{{source_file}}"
}`,
    },
}

const httpPresetOptions = Object.entries(HTTP_PRESETS)
    .map(([value, preset]) => ({ value, label: preset.label }))

/** Returns the default form state, pre-filled with the public Wikidata namespaces. */
function createDefaultForm() {
    return {
        id: '',
        label: '',
        description: '',
        type: 'sparql',
        http: {
            url: '',
            method: HTTP_PRESETS.wikibase.method,
            bodyType: HTTP_PRESETS.wikibase.bodyType,
            bodyTemplate: HTTP_PRESETS.wikibase.body,
            errorPath: HTTP_PRESETS.wikibase.errorPath,
            prepare: HTTP_PRESETS.wikibase.prepare.map((step) => ({ ...step })),
        },
        updateUrl: '',
        graphUri: '',
        timeoutSeconds: 30,
        bodyFormat: 'sparql-update',
        headers: [],
        useTemplate: false,
        updateTemplate: PRESETS.labels.text,
        auth: {
            type: 'none',
            username: '',
            password: '',
        },
        namespaces: {
            itemBaseUri: 'http://www.wikidata.org/entity/',
            propertyBaseUri: 'http://www.wikidata.org/prop/direct/',
        },
        knowledgeBase: {
            type: 'none',
            baseUrl: '',
        },
    }
}

const form = reactive(createDefaultForm())
const errors = reactive({})

const selectedPreset = ref('labels')
const selectedHttpPreset = ref('wikibase')

const isHttp = computed(() => form.type === 'http')
const targetTypeHint = computed(() => TARGET_TYPE_HINTS[form.type] || '')

const bodyFormatHint = computed(() => BODY_FORMATS[form.bodyFormat]?.hint || '')

// Picking an example replaces the body, and the steps that go with it.
watch(selectedHttpPreset, (key) => {
    const preset = HTTP_PRESETS[key]
    form.http.method = preset.method
    form.http.bodyType = preset.bodyType
    form.http.bodyTemplate = preset.body
    form.http.errorPath = preset.errorPath
    form.http.prepare = preset.prepare.map((step) => ({ ...step }))
})

function addPrepareStep() {
    form.http.prepare.push({
        name: '', method: 'GET', url: '', bodyTemplate: '', captureName: '', capturePath: '',
    })
}

function removePrepareStep(index) {
    form.http.prepare.splice(index, 1)
}

/** Live preview of where a published QID would be browsed, so the base URL is easy to get right. */
const kbSampleLink = computed(() => buildWikibaseLink('Q42', 'item', form.knowledgeBase.baseUrl.trim()))

// Picking an example replaces the textarea content with it.
watch(selectedPreset, (key) => {
    form.updateTemplate = PRESETS[key].text
})

function addHeader() {
    form.headers.push({ key: '', value: '' })
}

function removeHeader(index) {
    form.headers.splice(index, 1)
}

/** Clears all field-level errors. */
function clearErrors() {
    Object.keys(errors).forEach((key) => delete errors[key])
}

/** Converts the headers rows into a plain object, dropping rows with an empty key. */
function buildHeadersObject() {
    return form.headers.reduce((accumulator, header) => {
        const key = header.key.trim()
        if (key) {
            accumulator[key] = header.value.trim()
        }
        return accumulator
    }, {})
}

/** Validates an absolute http(s) URL, also rejecting characters illegal inside a SPARQL IRI. */
function validateUri(value, { required }) {
    if (!value) {
        return required ? 'This field is required.' : ''
    }
    if (!/^https?:\/\//.test(value)) {
        return 'URL must start with http:// or https://'
    }
    if (/[\s<>"{}|\\^`]/.test(value)) {
        return 'URL must not contain spaces or the characters <>"{}|\\^`'
    }
    return ''
}

/** Validates the form, populating `errors`. */
function validate() {
    clearErrors()

    const id = form.id.trim().toLowerCase()
    if (!id) {
        errors.id = 'Slug is required.'
    } else if (!SLUG_RE.test(id)) {
        errors.id = 'Use lowercase letters, digits, hyphens and underscores only.'
    } else if (props.existingIds.includes(id)) {
        errors.id = 'A target with this slug already exists.'
    }

    if (!form.label.trim()) {
        errors.label = 'Display name is required.'
    }

    if (isHttp.value) {
        validateHttpTarget()
    } else {
        const urlError = validateUri(form.updateUrl.trim(), { required: true })
        if (urlError) {
            errors.updateUrl = urlError === 'This field is required.' ? 'Update URL is required.' : urlError
        }

        const graphError = validateUri(form.graphUri.trim(), { required: false })
        if (graphError) {
            errors.graphUri = graphError
        }
    }

    const itemBaseError = validateUri(form.namespaces.itemBaseUri.trim(), { required: true })
    if (itemBaseError) {
        errors.itemBaseUri = itemBaseError
    }

    const propertyBaseError = validateUri(form.namespaces.propertyBaseUri.trim(), { required: true })
    if (propertyBaseError) {
        errors.propertyBaseUri = propertyBaseError
    }

    if (!Number.isInteger(form.timeoutSeconds) || form.timeoutSeconds < 1 || form.timeoutSeconds > 300) {
        errors.timeoutSeconds = 'Between 1 and 300.'
    }

    if (form.auth.type === 'basic') {
        if (!form.auth.username.trim()) {
            errors.username = 'Username is required for Basic auth.'
        }
        if (!form.auth.password) {
            errors.password = 'Password is required for Basic auth.'
        }
    }

    const badHeaderNames = form.headers
        .map((header) => header.key.trim())
        .filter((key) => key && !HEADER_NAME_RE.test(key))
    if (badHeaderNames.length > 0) {
        errors.headers = `Invalid header name(s): ${badHeaderNames.join(', ')}.`
    } else if (form.headers.some((header) => /[\r\n]/.test(header.value))) {
        errors.headers = 'Header values must not contain line breaks.'
    }

    if (form.knowledgeBase.type === 'wikibase') {
        const kbBaseError = validateUri(form.knowledgeBase.baseUrl.trim(), { required: true })
        if (kbBaseError) {
            errors.kbBaseUrl = kbBaseError === 'This field is required.'
                ? 'Base URL is required for a Wikibase instance.'
                : kbBaseError
        }
    }

    if (form.useTemplate && !isHttp.value) {
        const { template } = splitTemplate(form.updateTemplate)
        if (!template) {
            errors.updateTemplate = 'Write the SPARQL to send, or untick the checkbox above.'
        } else {
            const unknown = [...template.matchAll(/\{\{\s*([A-Za-z_]+)\s*\}\}/g)]
                .map((match) => match[1])
                .filter((name) => !KNOWN_PLACEHOLDERS.includes(name))
            if (unknown.length > 0) {
                errors.updateTemplate = `Unknown placeholder(s): ${[...new Set(unknown)].join(', ')}.`
            } else if (template.includes('{{graph}}') && !form.graphUri.trim()) {
                errors.updateTemplate = 'The template uses {{graph}} but no named graph URI is set above.'
            }
        }
    }

    return Object.keys(errors).length === 0
}

/**
 * Checks an HTTP target: its URL, a body that parses, and slots the backend can
 * actually fill — the built-in ones plus whatever the prepare steps capture. The
 * backend re-checks all of this; catching it here just saves a round-trip.
 */
function validateHttpTarget() {
    const urlError = validateUri(form.http.url.trim(), { required: true })
    if (urlError) {
        errors.httpUrl = urlError === 'This field is required.' ? 'URL is required.' : urlError
    }

    const body = form.http.bodyTemplate.trim()
    if (!body) {
        errors.httpBody = 'Write the request body to send.'
        return
    }

    if (form.http.bodyType !== 'raw') {
        try {
            const parsed = JSON.parse(body)
            if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
                errors.httpBody = 'The body must be a JSON object of fields.'
                return
            }
        } catch (e) {
            errors.httpBody = `The body is not valid JSON: ${e.message}`
            return
        }
    }

    const captured = form.http.prepare
        .map((step) => step.captureName.trim())
        .filter(Boolean)

    const badStep = form.http.prepare.find((step) => {
        const hasCapture = step.captureName.trim() || step.capturePath.trim()
        return !step.url.trim() || (hasCapture && !(step.captureName.trim() && step.capturePath.trim()))
    })
    if (badStep) {
        errors.prepare = 'Every step needs a URL, and a captured value needs both a slot name and a path.'
    }

    const badBody = form.http.prepare.find((step) => {
        const stepBody = (step.bodyTemplate || '').trim()
        if (step.method !== 'POST' || !stepBody) return false
        try {
            const parsed = JSON.parse(stepBody)
            return parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)
        } catch {
            return true
        }
    })
    if (badBody) {
        errors.prepare = `Step "${badBody.name || badBody.url}": the body must be a JSON object of fields.`
    }

    const known = [...KNOWN_HTTP_PLACEHOLDERS, ...captured]
    const unknown = [...body.matchAll(/\{\{\s*([A-Za-z_]+)\s*\}\}/g)]
        .map((match) => match[1])
        .filter((name) => !known.includes(name))
    if (unknown.length > 0) {
        errors.httpBody = `Unknown slot(s): ${[...new Set(unknown)].join(', ')}. `
            + 'Capture it in a step above, or fix the name.'
    }
}

/**
 * Splits the leading PREFIX/BASE/comment lines from the textarea content, so the
 * user writes one block of SPARQL while the prologue is still sent once per
 * request rather than repeated for every triple.
 */
function splitTemplate(text) {
    const lines = text.trim().split('\n')
    let bodyStart = 0
    while (bodyStart < lines.length) {
        const line = lines[bodyStart].trim()
        if (line === '' || line.startsWith('#') || /^(prefix|base)\s/i.test(line)) {
            bodyStart += 1
        } else {
            break
        }
    }
    const prefixes = lines.slice(0, bodyStart).map((l) => l.trim()).filter(Boolean).join('\n')
    const template = lines.slice(bodyStart).join('\n').trim()
    return { prefixes: prefixes || null, template: template || null }
}

/** Assembles the `request` and `prepare` parts of an HTTP target. */
function buildHttpTarget() {
    const body = form.http.bodyTemplate.trim()

    return {
        request: {
            method: form.http.method,
            url: form.http.url.trim(),
            body_type: form.http.bodyType,
            body_template: form.http.bodyType === 'raw' ? body : JSON.parse(body),
            error_path: form.http.errorPath.trim() || null,
        },
        prepare: form.http.prepare
            .filter((step) => step.url.trim())
            .map((step) => {
                const body = (step.bodyTemplate || '').trim()
                return {
                    name: step.name.trim() || 'step',
                    method: step.method,
                    url: step.url.trim(),
                    body_type: 'form',
                    ...(step.method === 'POST' && body && { body_template: JSON.parse(body) }),
                    capture: step.captureName.trim()
                        ? { [step.captureName.trim()]: step.capturePath.trim() }
                        : {},
                }
            }),
    }
}

/** Assembles the backend payload from the form state. */
function buildConfig() {
    const auth = { type: form.auth.type }
    if (form.auth.type === 'basic') {
        auth.username = form.auth.username.trim()
        auth.password = form.auth.password
    }

    const headers = buildHeadersObject()
    const shape = form.useTemplate ? splitTemplate(form.updateTemplate) : { prefixes: null, template: null }

    return {
        id: form.id.trim().toLowerCase(),
        label: form.label.trim(),
        description: form.description.trim() || null,
        type: form.type,
        ...(isHttp.value ? buildHttpTarget() : {
            update_url: form.updateUrl.trim(),
            graph_uri: form.graphUri.trim() || null,
            body_format: form.bodyFormat,
            prefixes: shape.prefixes,
            update_template: shape.template,
        }),
        timeout_seconds: form.timeoutSeconds,
        ...(Object.keys(headers).length > 0 && { headers }),
        auth,
        namespaces: {
            item_base_uri: form.namespaces.itemBaseUri.trim(),
            property_base_uri: form.namespaces.propertyBaseUri.trim(),
        },
        knowledge_base: {
            type: form.knowledgeBase.type,
            ...(form.knowledgeBase.type === 'wikibase' && {
                base_url: form.knowledgeBase.baseUrl.trim(),
            }),
        },
    }
}

function onSubmit() {
    if (!validate()) {
        return
    }
    emit('submit', buildConfig())
}

/** Restores the pristine form state. */
function resetForm() {
    Object.assign(form, createDefaultForm())
    selectedPreset.value = 'labels'
    selectedHttpPreset.value = 'wikibase'
    clearErrors()
}

defineExpose({ resetForm })
</script>

<style scoped>
.sink-form {
    --ods-gray-300: #ddd;
    --ods-gray-700: #595959;
}

.form-section {
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.5rem;
    padding: 1rem 1.25rem 1.25rem;
    margin-bottom: 1.25rem;
}

.form-section-title {
    float: none;
    width: auto;
    padding: 0 0.5rem;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--ods-gray-700);
}

.field-hint {
    font-size: 0.8rem;
    color: var(--ods-gray-700);
    margin: 0.35rem 0 0;
}

.field-error {
    font-size: 0.8rem;
    font-weight: 600;
    color: #cd3c14;
    margin: 0.35rem 0 0;
}

.template-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.75rem;
    font-weight: 700;
    cursor: pointer;
}

.placeholder-details {
    margin-top: 0.5rem;
    font-size: 0.85rem;
}

.placeholder-details summary {
    cursor: pointer;
    color: var(--ods-gray-700);
}

.placeholder-list {
    list-style: none;
    padding: 0;
    margin: 0.5rem 0 0;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}

.placeholder-group-title {
    display: inline-block;
    min-width: 6rem;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--ods-gray-700);
}

.placeholder-chip {
    display: inline-block;
    margin-right: 0.35rem;
    padding: 0.05rem 0.3rem;
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.2rem;
    font-size: 0.75rem;
}

.template-warning {
    margin: 0.75rem 0 0;
    padding: 0.5rem 0.75rem;
    border-radius: 0.4rem;
    background: #fff6e0;
    color: #8a6d00;
    font-size: 0.8rem;
}

.prepare-step {
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.4rem;
    padding: 0.75rem;
    margin-top: 0.75rem;
}

.header-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) auto;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}

.header-remove-btn {
    border: 0.1rem solid var(--ods-gray-300);
    background: transparent;
    color: #cd3c14;
    border-radius: 0.3rem;
    padding: 0 0.6rem;
    cursor: pointer;
}

.add-row-button {
    border: 0.1rem dashed var(--ods-gray-300);
    background: transparent;
    border-radius: 0.3rem;
    padding: 0.25rem 0.75rem;
    font-size: 0.85rem;
    cursor: pointer;
}

.add-row-button:hover {
    border-color: #ff7900;
    color: #ff7900;
}
</style>
