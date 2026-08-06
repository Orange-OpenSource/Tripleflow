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
    <div
        class="triple-card-shell"
        :class="{ 'is-source-linked': hasSourceInput }"
        @click="handleCardClick"
    >
        <Card extraClass="mb-3">
        <div class="d-flex justify-content-between align-items-start gap-3">
            <div class="flex-grow-1">
                <TripleSchema :triple="triple" :extractor="extractor" />
            </div>
            <Button
                variant="outline-secondary"
                @click.stop="toggleDetails"
            >
                {{ isOpen ? 'Hide details' : 'Show details' }}
            </Button>
        </div>
        <TripleMetadata v-if="isOpen" :triple="triple" :extractor="extractor" />
        </Card>
    </div>
</template>

<script setup>
/**
 * Displays a single triple with a collapsible metadata panel.
 * Emits 'focus-source-input' with the source input index when the card is clicked
 * (only if the triple has a known source input index).
 */
import { computed, ref } from 'vue'
import Button from '../atoms/Button.vue'
import Card from '../atoms/Card.vue'
import TripleSchema from '../molecules/TripleSchema.vue'
import TripleMetadata from '../molecules/TripleMetadata.vue'

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
const emit = defineEmits(['focus-source-input'])

const isOpen = ref(false)
const hasSourceInput = computed(() => {
    return typeof props.triple?.sourceInputIndex === 'number'
})

/** Toggles the TripleMetadata panel open or closed. */
function toggleDetails() {
    isOpen.value = !isOpen.value
}

/** Emits focus-source-input so the parent can highlight and scroll to the corresponding input text block. */
function handleCardClick() {
    if (!hasSourceInput.value) {
        return
    }

    emit('focus-source-input', props.triple.sourceInputIndex)
}
</script>

<style scoped>
.triple-card-shell {
    padding: 0;
    border-radius: 0.9rem;
}

.triple-card-shell :deep(.card) {
    margin-bottom: 0;
    border: 1px solid #ececec;
    box-shadow: 0 0.35rem 1rem rgba(0, 0, 0, 0.03);
}
</style>
