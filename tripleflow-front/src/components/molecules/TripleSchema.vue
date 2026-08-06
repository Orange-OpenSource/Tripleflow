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
    <div class="triple-schema d-flex align-items-center flex-wrap gap-2">
        <a
            v-if="subjectHref"
            class="triple-link"
            :href="subjectHref"
            target="_blank"
            rel="noopener noreferrer"
        >
            <Badge badgeClass="text-bg-light">{{ subjectLabel }}</Badge>
        </a>
        <Badge v-else badgeClass="text-bg-light">{{ subjectLabel }}</Badge>

        <span class="fw-bold">-></span>

        <a
            v-if="predicateHref"
            class="triple-link"
            :href="predicateHref"
            target="_blank"
            rel="noopener noreferrer"
        >
            <Badge badgeClass="text-bg-dark">{{ predicateLabel }}</Badge>
        </a>
        <Badge v-else badgeClass="text-bg-dark">{{ predicateLabel }}</Badge>

        <span class="fw-bold">-></span>

        <a
            v-if="objHref"
            class="triple-link"
            :href="objHref"
            target="_blank"
            rel="noopener noreferrer"
        >
            <Badge badgeClass="text-bg-light">{{ objLabel }}</Badge>
        </a>
        <Badge v-else badgeClass="text-bg-light">{{ objLabel }}</Badge>
    </div>
</template>

<script setup>
/**
 * Renders a triple as "Subject → Predicate → Object" using colored badges.
 * Each entity becomes a knowledge-base link when it has a valid Wikidata-style ID.
 */
import { computed } from 'vue'
import Badge from '../atoms/Badge.vue'
import { isNullLikeEntityValue } from '../../composables/entity.js'
import { buildEntityLink } from '../../composables/entityLinks.js'

const props = defineProps({
    triple: {
        type: Object,
        required: true,
    },
    extractor: {
        type: String,
        default: '',
    },
})

function normalizeDisplayLabel(value, fallback) {
    if (isNullLikeEntityValue(value)) {
        return fallback
    }

    return String(value).trim()
}

function normalizeEntityId(value) {
    if (isNullLikeEntityValue(value)) {
        return ''
    }

    return String(value).trim()
}

const subjectLabel = computed(() => {
    return normalizeDisplayLabel(props.triple?.subject?.label ?? props.triple?.subject, 'Unknown subject')
})

const subjectId = computed(() => {
    return normalizeEntityId(props.triple?.subject?.id ?? props.triple?.subject?.qid)
})

const subjectHref = computed(() => {
    return buildEntityLink(subjectId.value, 'item', props.extractor)
})

const predicateLabel = computed(() => {
    return normalizeDisplayLabel(props.triple?.predicate?.label ?? props.triple?.predicate, 'Unknown predicate')
})

const predicateId = computed(() => {
    return normalizeEntityId(props.triple?.predicate?.id ?? props.triple?.predicate?.pid)
})

const predicateHref = computed(() => {
    return buildEntityLink(predicateId.value, 'property', props.extractor)
})

const objLabel = computed(() => {
    return normalizeDisplayLabel(props.triple?.obj?.label ?? props.triple?.obj, 'Unknown object')
})

const objId = computed(() => {
    return normalizeEntityId(props.triple?.obj?.id ?? props.triple?.obj?.qid)
})

const objHref = computed(() => {
    return buildEntityLink(objId.value, 'item', props.extractor)
})
</script>

<style scoped>
.triple-link {
    text-decoration: none;
}
</style>
