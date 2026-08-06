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
    <input
        ref="fileInput"
        :id="id"
        type="file"
        :class="['form-control', extraClass]"
        :accept="accept"
        :multiple="multiple"
        @change="handleChange"
    />
</template>

<script setup>
/**
 * File input element that emits the selected File array via 'update:file'.
 * Exposes a clear() method to reset the native input (allows re-selecting the same file).
 */
import { ref } from 'vue'

const fileInput = ref(null)
const emit = defineEmits(['update:file'])

defineProps({
    id: {
        type: String,
        default: ''
    },
    accept: {
        type: String,
        default: '.txt, .pdf, text/plain, application/pdf'
    },
    multiple: {
        type: Boolean,
        default: false
    },
    extraClass: {
        type: String,
        default: ''
    }
})

/** Emits the selected File array when the user picks files, or null if the selection is empty. */
function handleChange(event){
    const files = Array.from(event.target.files || [])
    emit('update:file', files.length > 0 ? files : null)
}

/** Resets the native file input so the same file can be selected again. */
function clear(){
    if(fileInput.value) {
        fileInput.value.value = ''
    }
}

defineExpose({ clear })
</script>
