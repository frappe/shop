<template>
	<div
		class="flex items-end gap-2 rounded-xl border border-outline-gray-2 bg-surface-white p-2 shadow-sm focus-within:border-outline-gray-4"
	>
		<textarea
			ref="input"
			v-model="text"
			rows="1"
			:disabled="disabled"
			:placeholder="placeholder || 'Ask the assistant to check or change something'"
			class="max-h-40 flex-1 resize-none border-0 bg-transparent px-2 py-1.5 text-base leading-6 text-ink-gray-9 placeholder:text-ink-gray-4 focus:outline-none focus:ring-0 disabled:text-ink-gray-5"
			data-shop="agent-input"
			@input="resize"
			@keydown.enter.exact.prevent="submit"
		/>
		<Button
			variant="solid"
			:disabled="disabled || !text.trim()"
			data-shop="agent-send"
			@click="submit"
		>
			<template #icon><LucideArrowUp class="size-4" /></template>
		</Button>
	</div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { Button } from 'frappe-ui'

import LucideArrowUp from '~icons/lucide/arrow-up'

const props = defineProps<{ disabled?: boolean; placeholder?: string }>()

const emit = defineEmits<{ send: [message: string] }>()

const text = ref('')
const input = ref<HTMLTextAreaElement | null>(null)

function resize() {
	const element = input.value
	if (!element) return
	element.style.height = 'auto'
	element.style.height = `${element.scrollHeight}px`
}

function submit() {
	const message = text.value.trim()
	if (!message || props.disabled) return
	text.value = ''
	nextTick(resize)
	emit('send', message)
}

function focus() {
	input.value?.focus()
}

defineExpose({ focus })
</script>
