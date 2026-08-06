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
    <select
        :id="id"
        :value="modelValue"
        :class="['form-select', extraClass]"
        @change="$emit('update:modelValue', $event.target.value)"
    >
        <option
            v-for="option in options"
            :key="option.value"
            :value="option.value"
        >
            {{ option.label }}
        </option>
    </select>
</template>

<script setup>
/** Bootstrap select element bound with v-model. Renders one option per entry in the options prop array. */
defineProps({
    modelValue: {
        type: String,
        default: '',
    },
    id: {
        type: String,
        default: '',
    },
    options: {
        type: Array,
        default: () => [],
    },
    extraClass: {
        type: String,
        default: '',
    },
})

defineEmits(['update:modelValue'])
</script>
