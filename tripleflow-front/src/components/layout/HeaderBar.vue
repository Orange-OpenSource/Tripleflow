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
  <header class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">

      <a class="navbar-brand d-flex align-items-center gap-2" href="#" @click.prevent="emit('navigate', 'home')">
        <img src="/orange-logo.svg" alt="TripleFlow logo" height="24" />
        <span class="fw-bold text-white">TripleFlow</span>
      </a>

      <nav class="navbar-nav ms-4 d-flex flex-row gap-4">
        <a
          class="nav-link"
          :class="{ active: currentPage === 'home' }"
          href="#"
          @click.prevent="emit('navigate', 'home')"
        >Extraction</a>
        <a
          class="nav-link"
          :class="{ active: currentPage === 'validation' }"
          href="#"
          @click.prevent="emit('navigate', 'validation')"
        >Validation</a>
        <a
          class="nav-link"
          :class="{ active: currentPage === 'graph' }"
          href="#"
          @click.prevent="emit('navigate', 'graph')"
        >Graph</a>
        <a
          class="nav-link"
          :class="{ active: currentPage === 'extractors' }"
          href="#"
          @click.prevent="emit('navigate', 'extractors')"
        >Extractors</a>
        <a
          class="nav-link"
          :class="{ active: currentPage === 'targets' }"
          href="#"
          @click.prevent="emit('navigate', 'targets')"
        >Targets</a>
      </nav>

    </div>
  </header>
</template>


<script setup>
/**
 * Top navigation bar with the TripleFlow logo and links to every page.
 * Emits 'navigate' with the target page name when a link is clicked.
 */
defineProps({
  currentPage: {
    type: String,
    default: 'home',
  },
})

const emit = defineEmits(['navigate'])
</script>
