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
    <textarea
        :id="id"
        :value="modelValue"
        :class="['form-control', 'w-100', extraClass]"
        :rows="rows"
        :placeholder="placeholder"
        @input="$emit('update:modelValue', $event.target.value)"
    ></textarea>
</template>

<script setup>
/** Bootstrap textarea bound with v-model. Emits 'update:modelValue' on every keystroke. */
defineProps({
    modelValue: {
        type: String,
        default: '',
    },
    id: {
        type: String,
        default: '',
    },
    rows: {
        type: [Number, String],
        default: 6,
    },
    placeholder: {
        type: String,
        default: '',
    },
    extraClass: {
        type: String,
        default: '',
    },
})

defineEmits(['update:modelValue'])
</script>
