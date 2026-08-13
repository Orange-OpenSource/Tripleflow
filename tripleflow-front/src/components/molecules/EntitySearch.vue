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

        <ul v-if="open && suggestions.length > 0" class="ac-dropdown" role="listbox">
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
        </ul>

        <div v-else-if="open && isSearching" class="ac-state">Searching…</div>

        <input
            class="edit-input edit-input-id"
            :value="modelValue.id"
            placeholder="ID (optional)"
            @input="$emit('update:modelValue', { ...modelValue, id: $event.target.value })"
        />
    </div>
</template>

<script setup>
/**
 * Autocomplete input for searching knowledge-base entities (items or properties),
 * through the backend /search/entities proxy. The backend picks the search API
 * from the extractor's declared knowledge base (public Wikidata by default).
 * Emits 'update:modelValue' with { label, id } on selection or manual input.
 * Supports keyboard navigation.
 */
import { ref } from 'vue'

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
let timer = null

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
</style>
