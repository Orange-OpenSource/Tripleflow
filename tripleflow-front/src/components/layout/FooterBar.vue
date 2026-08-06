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
        <footer class="footer navbar" data-bs-theme="dark">
            <h2 class="visually-hidden">Sitemap & information</h2>
            <div class="container-xxl footer-terms">
                <ul class="navbar-nav gap-md-3">
                    <li class="fw-bold">© {{ currentYear }} TripleFlow</li>
                    <li v-for="link in footerLinks" :key="link.href">
                        <a class="nav-link" :href="link.href" target="_blank">{{ link.label }}</a>
                    </li>
                </ul>
            </div>
        </footer>
</template>

<script setup>
/**
 * Footer with instance-specific links (terms of service, knowledge base, support…)
 * provided by the VITE_FOOTER_LINKS env var as a JSON array of { label, href }.
 * No link is shown when the variable is unset, keeping the codebase deployment-agnostic.
 */
const currentYear = new Date().getFullYear()

function parseFooterLinks(raw) {
    if (typeof raw !== 'string' || raw.trim() === '') {
        return []
    }

    try {
        const parsed = JSON.parse(raw)
        return Array.isArray(parsed)
            ? parsed.filter((link) => link && typeof link.label === 'string' && typeof link.href === 'string')
            : []
    } catch {
        return []
    }
}

const footerLinks = parseFooterLinks(import.meta.env.VITE_FOOTER_LINKS)
</script>
