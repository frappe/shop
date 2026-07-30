<template>
	<div class="flex flex-col gap-3">
		<div
			v-for="(question, index) in questions"
			:key="keyOf(question, index)"
			class="rounded-lg border border-outline-gray-2 bg-surface-white p-4"
			data-shop="agent-approval"
		>
			<div class="flex items-center gap-2">
				<LucideShieldAlert class="size-4 shrink-0 text-ink-amber-6" />
				<h3 class="text-base font-medium text-ink-gray-9">Approve {{ parse(question).tool }}</h3>
			</div>
			<p class="mt-1 text-sm text-ink-gray-6">
				This changes your store. Check the details before you approve.
			</p>
			<pre
				v-if="parse(question).body"
				class="mt-3 overflow-x-auto rounded bg-surface-gray-2 p-3 font-mono text-xs leading-5 text-ink-gray-8"
				>{{ parse(question).body }}</pre
			>
			<div class="mt-3 flex items-center gap-2">
				<Button
					v-for="option in optionsOf(question)"
					:key="option"
					:variant="option === 'Approve' ? 'solid' : 'subtle'"
					:theme="option === 'Deny' ? 'red' : 'gray'"
					:disabled="submitting"
					:loading="submitting && chosen[keyOf(question, index)] === option"
					@click="choose(question, index, option)"
				>
					{{ option }}
				</Button>
				<span v-if="chosen[keyOf(question, index)] && questions.length > 1" class="text-sm text-ink-gray-5">
					{{ chosen[keyOf(question, index)] }} selected
				</span>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Button } from 'frappe-ui'

import LucideShieldAlert from '~icons/lucide/shield-alert'

export interface AgentQuestion {
	prompt: string
	options?: string[]
	multi_select?: boolean
	allow_other?: boolean
	key?: string | null
}

const props = defineProps<{
	questions: AgentQuestion[]
	submitting?: boolean
}>()

const emit = defineEmits<{ submit: [answers: Record<string, string>] }>()

const chosen = ref<Record<string, string>>({})

const keyOf = (question: AgentQuestion, index: number) => question.key || `question-${index}`

const optionsOf = (question: AgentQuestion) => question.options?.length ? question.options : ['Approve', 'Deny']

function parse(question: AgentQuestion) {
	const [heading, ...rest] = (question.prompt || '').split('\n\n')
	const tool = heading.match(/`([^`]+)`/)?.[1] || 'this change'
	return { tool, body: pretty(rest.join('\n\n').trim()) }
}

function pretty(body: string) {
	try {
		return JSON.stringify(JSON.parse(body), null, 2)
	} catch (error) {
		return body
	}
}

function choose(question: AgentQuestion, index: number, option: string) {
	if (props.submitting) return
	chosen.value[keyOf(question, index)] = option
	const answered = props.questions.every((item, position) => chosen.value[keyOf(item, position)])
	if (answered) emit('submit', { ...chosen.value })
}
</script>
