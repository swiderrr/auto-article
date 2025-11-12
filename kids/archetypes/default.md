---
title: "{{ replace .Name "-" " " | title }}"
date: {{ .Date }}
draft: false
tags: []
categories: []
authors: ["Your Name"]
summary: ""
featured_image: ""
slug: "{{ .Name }}"
seo:
  description: ""
  meta_description: "" # legacy key kept for compatibility
  canonical: ""

<!-- Guidelines: the site prefers substantive, helpful articles to satisfy AdSense.
Minimum recommendations enforced by tools:
- meta.description / seo.description: 120-160 characters
- article body: minimum 600 words
- featured_image: encouraged
-->
---
