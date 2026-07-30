<template>
	<Dropdown :options="options" placement="right">
		<Button>
			<template #prefix><LucideHistory class="size-4" /></template>
			History
		</Button>
	</Dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, Dropdown } from 'frappe-ui'

import LucideHistory from '~icons/lucide/history'

export interface AgentSession {
	name: string
	title?: string | null
	modified?: string
}

const props = defineProps<{ sessions: AgentSession[]; current?: string | null }>()

const emit = defineEmits<{ select: [name: string] }>()

const options = computed(() => {
	if (!props.sessions.length) return [{ label: 'No chats yet', onClick: () => {}, disabled: true }]
	return props.sessions.map((chat) => ({
		label: `${chat.title || 'Untitled chat'} · ${when(chat.modified)}`,
		onClick: () => emit('select', chat.name),
		active: chat.name === props.current,
	}))
})

function when(modified?: string) {
	if (!modified) return ''
	const date = new Date(modified.replace(' ', 'T'))
	const sameDay = date.toDateString() === new Date().toDateString()
	return sameDay
		? date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
		: date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}
</script>
