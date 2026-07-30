<template>
	<div v-if="role === 'user'" class="flex justify-end">
		<div
			class="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-surface-gray-3 px-4 py-2.5 text-base leading-7 text-ink-gray-9"
		>
			{{ content }}
		</div>
	</div>
	<div v-else class="flex flex-col gap-1.5">
		<div v-if="tools?.length" class="flex items-center gap-1.5 text-xs text-ink-gray-5">
			<LucideWrench class="size-3 shrink-0" />
			<span class="truncate">Used {{ tools.join(', ') }}</span>
		</div>
		<div
			v-if="content"
			class="whitespace-pre-wrap text-base leading-7 text-ink-gray-8"
			v-html="html"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import LucideWrench from '~icons/lucide/wrench'

const props = defineProps<{
	role: string
	content?: string | null
	tools?: string[]
}>()

const escapes: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;' }

const html = computed(() =>
	(props.content || '')
		.replace(/[&<>]/g, (character) => escapes[character])
		.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-ink-gray-9">$1</strong>')
		.replace(
			/`([^`\n]+)`/g,
			'<code class="rounded bg-surface-gray-2 px-1 py-0.5 font-mono text-sm">$1</code>',
		),
)
</script>
