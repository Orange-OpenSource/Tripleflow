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
    <div class="card" :class="extraClass">
        <div class="card-body">
            <slot />
        </div>
    </div>
</template>

<script setup>
/** Bootstrap card wrapper with a single slot for body content. Use extraClass to add classes to the card element. */
    defineProps({
        extraClass:{
            type: String,
            default: ''
        }
    })
</script>
