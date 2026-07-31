<template>
	<span>
		<template v-for="(part, index) in parts" :key="index">
			<a
				v-if="part.href"
				:href="part.href"
				target="_blank"
				class="text-ink-gray-8 underline hover:text-ink-gray-9"
				@click.stop
			>
				{{ part.text }}
			</a>
			<template v-else>{{ part.text }}</template>
		</template>
	</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ text: string }>()

const TRAILING_PUNCTUATION = /[.,;:!?)'"]+$/

const parts = computed(() => props.text.split(/(\s+)/).flatMap(tokenParts))

function tokenParts(token: string) {
	const path = token.replace(TRAILING_PUNCTUATION, '')
	if (!path.startsWith('/')) return [{ text: token }]
	const trailing = token.slice(path.length)
	return trailing ? [{ text: path, href: path }, { text: trailing }] : [{ text: path, href: path }]
}
</script>
