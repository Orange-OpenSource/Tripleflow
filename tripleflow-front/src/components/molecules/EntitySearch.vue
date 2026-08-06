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
    <div class="entity-ac" @focusout="onContainerFocusout">
        <input
            class="edit-input"
            :value="modelValue.label"
            :placeholder="placeholder"
            autocomplete="off"
            @input="onLabelInput"
            @keydown="onKeydown"
            @focus="onFocus"
        />

        <ul v-if="open && (suggestions.length > 0 || canCreate)" class="ac-dropdown" role="listbox">
            <li
                v-for="(s, i) in suggestions"
                :key="s.id || i"
                :class="['ac-item', { 'is-active': i === activeIndex }]"
                role="option"
                @mousedown.prevent
                @click="select(s)"
            >
                <span class="ac-label">{{ s.label }}</span>
                <span class="ac-id">{{ s.id }}</span>
                <span v-if="s.description" class="ac-desc">{{ s.description }}</span>
            </li>

            <li v-if="canCreate" class="ac-item ac-create" @mousedown.prevent @click="openCreateForm">
                + Create "{{ searchQuery }}"
            </li>
        </ul>

        <div v-else-if="open && isSearching" class="ac-state">Searching…</div>

        <input
            class="edit-input edit-input-id"
            :value="modelValue.id"
            placeholder="ID (optional)"
            @input="$emit('update:modelValue', { ...modelValue, id: $event.target.value })"
        />

        <div v-if="showCreateForm" class="create-form">
            <p class="create-title">New {{ type }}</p>
            <div class="create-fields">
                <div class="create-field">
                    <label class="create-label">Label</label>
                    <input class="edit-input" v-model="createLabel" placeholder="Label" />
                </div>
                <div class="create-field">
                    <label class="create-label">Alias</label>
                    <input class="edit-input" v-model="createAlias" placeholder="Alias (optional)" />
                </div>
            </div>
            <div class="create-actions">
                <button type="button" class="btn-create" @click="confirmCreate">Create</button>
                <button type="button" class="btn-cancel" @click="cancelCreate">Cancel</button>
            </div>
        </div>
    </div>
</template>

<script setup>
/**
 * Autocomplete input for searching knowledge-base entities (items or properties),
 * through the backend /search/entities proxy. The backend picks the search API
 * from the extractor's declared knowledge base (public Wikidata by default).
 * Emits 'update:modelValue' with { label, id } on selection or manual input.
 * Supports keyboard navigation and an inline form to create new entities.
 */
import { computed, ref } from 'vue'

import { DEFAULT_API_BASE_URL } from '../../composables/extraction/constants'

const props = defineProps({
    modelValue: { type: Object, required: true },
    type: { type: String, default: 'item' },
    placeholder: { type: String, default: 'Label' },
    extractor: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const suggestions = ref([])
const isSearching = ref(false)
const open = ref(false)
const activeIndex = ref(-1)
const searchQuery = ref('')
let timer = null

const showCreateForm = ref(false)
const createLabel = ref('')
const createAlias = ref('')

const canCreate = computed(() => searchQuery.value.length >= 2 && !isSearching.value)

/**
 * Fires a search request to the backend entity-search proxy and populates the
 * suggestions list. Knowledge bases without a search API answer 503, in
 * which case the list simply stays empty.
 * @param {string} q - search query (at least 2 characters)
 */
async function doSearch(q) {
    isSearching.value = true
    try {
        const extractorParam = props.extractor ? `&extractor=${encodeURIComponent(props.extractor)}` : ''
        const url = `${DEFAULT_API_BASE_URL}/search/entities?type=${props.type}&limit=7&q=${encodeURIComponent(q)}${extractorParam}`
        const resp = await fetch(url)
        const data = resp.ok ? await resp.json() : {}
        suggestions.value = (data.results || []).map(s => ({
            id: s.id,
            label: s.label || s.id,
            description: s.description || '',
        }))
    } catch {
        suggestions.value = []
    } finally {
        isSearching.value = false
    }
}

/** Debounces the search: waits 300ms after the user stops typing before calling doSearch. */
function search(q) {
    clearTimeout(timer)
    if (!q || q.length < 2) { suggestions.value = []; return }
    timer = setTimeout(() => doSearch(q), 300)
}

/** Cancels any pending search and resets the suggestions list. */
function clear() {
    clearTimeout(timer)
    suggestions.value = []
    isSearching.value = false
}

/** Handles text input: updates modelValue, resets the ID, and triggers a debounced search. */
function onLabelInput(e) {
    searchQuery.value = e.target.value
    emit('update:modelValue', { ...props.modelValue, label: e.target.value, id: '' })
    open.value = true
    activeIndex.value = -1
    search(e.target.value)
}

/** Re-opens the dropdown if suggestions are already loaded when the input receives focus. */
function onFocus() {
    if (suggestions.value.length > 0) open.value = true
}

/** Selects a suggestion, emits the chosen { label, id }, and closes the dropdown. */
function select(s) {
    emit('update:modelValue', { label: s.label, id: s.id })
    open.value = false
    clear()
}

/** Opens the inline creation form pre-filled with the current search query. */
function openCreateForm() {
    createLabel.value = searchQuery.value
    createAlias.value = ''
    open.value = false
    showCreateForm.value = true
}

/** Emits a new entity with the entered label (ID left empty) and closes the creation form. */
function confirmCreate() {
    emit('update:modelValue', { label: createLabel.value, id: '' })
    showCreateForm.value = false
}

/** Closes the creation form without emitting a value. */
function cancelCreate() {
    showCreateForm.value = false
}

/** Handles keyboard navigation (ArrowUp/Down to move, Enter to select, Escape to close). */
function onKeydown(e) {
    if (!open.value || !suggestions.value.length) return
    if (e.key === 'ArrowDown') {
        e.preventDefault()
        activeIndex.value = Math.min(activeIndex.value + 1, suggestions.value.length - 1)
    } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        activeIndex.value = Math.max(activeIndex.value - 1, -1)
    } else if (e.key === 'Enter' && activeIndex.value >= 0) {
        e.preventDefault()
        select(suggestions.value[activeIndex.value])
    } else if (e.key === 'Escape') {
        open.value = false
        activeIndex.value = -1
    }
}

/** Closes the dropdown when focus leaves the entire container (not just the input). */
function onContainerFocusout(e) {
    if (!e.currentTarget.contains(e.relatedTarget)) {
        open.value = false
        activeIndex.value = -1
    }
}
</script>

<style scoped>
.entity-ac {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}

.ac-dropdown {
    position: absolute;
    top: calc(100% - 0.35rem);
    left: 0;
    right: 0;
    z-index: 50;
    background: #fff;
    border: 0.1rem solid #ddd;
    border-radius: 0.25rem;
    box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.1);
    max-height: 14rem;
    overflow-y: auto;
    list-style: none;
    margin: 0;
    padding: 0.25rem 0;
}

.ac-item {
    display: grid;
    grid-template-columns: 1fr auto;
    grid-template-rows: auto auto;
    column-gap: 0.5rem;
    padding: 0.45rem 0.75rem;
    cursor: pointer;
    transition: background 0.1s;
}

.ac-item:hover,
.ac-item.is-active {
    background: #ff7900;
    color: #fff;
}

.ac-item.is-active .ac-id,
.ac-item.is-active .ac-desc,
.ac-item:hover .ac-id,
.ac-item:hover .ac-desc {
    color: rgba(255, 255, 255, 0.8);
}

.ac-create {
    display: block;
    border-top: 0.1rem solid #eee;
    font-size: 0.8rem;
    color: #ff7900;
    font-weight: 500;
}

.ac-create:hover {
    background: rgba(255, 121, 0, 0.08);
    color: #ff7900;
}

.ac-label {
    font-size: 0.85rem;
    font-weight: 500;
    grid-column: 1;
    grid-row: 1;
}

.ac-id {
    font-size: 0.7rem;
    color: #999;
    grid-column: 2;
    grid-row: 1;
    align-self: center;
    font-family: var(--bs-font-monospace);
}

.ac-desc {
    font-size: 0.75rem;
    color: #595959;
    font-style: italic;
    grid-column: 1 / -1;
    grid-row: 2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.ac-state {
    position: absolute;
    top: calc(100% - 0.35rem);
    left: 0;
    right: 0;
    z-index: 50;
    background: #fff;
    border: 0.1rem solid #ddd;
    border-radius: 0.25rem;
    padding: 0.5rem 0.75rem;
    font-size: 0.8rem;
    color: #999;
}

.edit-input {
    border: 0.1rem solid #ddd;
    border-radius: 0.25rem;
    padding: 0.3rem 0.65rem;
    font-size: 0.85rem;
    outline: none;
    font-family: inherit;
    transition: border-color 0.15s;
}

.edit-input:focus {
    border-color: #ff7900;
}

.edit-input-id {
    font-size: 0.75rem;
    color: #595959;
}

.create-form {
    border: 0.1rem solid #ddd;
    border-radius: 0.25rem;
    padding: 0.75rem;
    background: #fff;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.create-title {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 700;
    color: #595959;
    margin: 0;
}

.create-fields {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}

.create-field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.create-label {
    font-size: 0.7rem;
    color: #999;
}

.create-actions {
    display: flex;
    gap: 0.5rem;
}

.btn-create {
    font-size: 0.8rem;
    font-family: inherit;
    padding: 0.25rem 0.75rem;
    background: #ff7900;
    color: #fff;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
}

.btn-create:hover {
    background: #f16e00;
}

.btn-cancel {
    font-size: 0.8rem;
    font-family: inherit;
    padding: 0.25rem 0.75rem;
    background: transparent;
    color: #595959;
    border: 0.1rem solid #ddd;
    border-radius: 0.25rem;
    cursor: pointer;
}

.btn-cancel:hover {
    border-color: #999;
}
</style>
