<template>
	<div class="flex h-full flex-col">
		<div v-if="status.loading && !status.data" class="flex flex-1 items-center justify-center">
			<LoadingIndicator class="size-5 text-ink-gray-5" />
		</div>

		<AgentNotReady v-else-if="!ready" :reason="status.data?.reason" />

		<template v-else>
			<header
				class="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-outline-gray-1 px-6"
			>
				<div class="flex items-baseline gap-2">
					<h1 class="text-base font-semibold text-ink-gray-9">Assistant</h1>
					<span class="text-sm text-ink-gray-5">{{ status.data?.model }}</span>
				</div>
				<div class="flex items-center gap-2">
					<AgentSessions
						:sessions="sessions.data || []"
						:current="sessionId"
						@select="openSession"
					/>
					<Button variant="subtle" data-shop="agent-new-chat" @click="newChat">
						<template #prefix><LucidePlus class="size-4" /></template>
						New chat
					</Button>
				</div>
			</header>

			<div ref="scroller" class="flex-1 overflow-y-auto">
				<div
					class="mx-auto flex min-h-full w-full max-w-[820px] flex-col gap-6 px-6 py-8"
					:class="{ 'justify-center': !visible.length && !busy }"
				>
					<AgentSuggestions v-if="!visible.length && !busy" @pick="send" />

					<AgentMessage
						v-for="(message, index) in visible"
						:key="index"
						:role="message.role"
						:content="message.content"
						:tools="message.tools"
					/>

					<AgentTyping v-if="busy" />

					<AgentApproval
						v-if="questions.length && !busy"
						:key="runId || 'pending'"
						:questions="questions"
						:submitting="answering"
						@submit="answer"
					/>

					<div
						v-if="error"
						class="rounded-lg border border-outline-red-1 bg-surface-red-1 p-4"
						data-shop="agent-error"
					>
						<div class="text-base font-medium text-ink-red-6">The assistant stopped</div>
						<p class="mt-1 whitespace-pre-wrap text-sm leading-6 text-ink-gray-7">{{ error }}</p>
						<Button v-if="lastMessage" class="mt-3" @click="retry">Retry</Button>
					</div>
				</div>
			</div>

			<div class="shrink-0 px-6 pb-6">
				<div class="mx-auto w-full max-w-[820px]">
					<AgentComposer :disabled="busy || answering" @send="send" />
					<p class="mt-2 text-center text-xs text-ink-gray-4">
						Enter to send, Shift and Enter for a new line. Changes need your approval.
					</p>
				</div>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Button, LoadingIndicator, call, createResource } from 'frappe-ui'

import LucidePlus from '~icons/lucide/plus'

import AgentApproval, { type AgentQuestion } from '@/components/AgentApproval.vue'
import AgentComposer from '@/components/AgentComposer.vue'
import AgentMessage from '@/components/AgentMessage.vue'
import AgentNotReady from '@/components/AgentNotReady.vue'
import AgentSessions from '@/components/AgentSessions.vue'
import AgentSuggestions from '@/components/AgentSuggestions.vue'
import AgentTyping from '@/components/AgentTyping.vue'

interface AgentMessageRow {
	role: string
	content?: string | null
	tools?: string[]
}

interface AgentRun {
	name: string
	session: string
	status: string
	output?: string
	error?: string
	questions?: AgentQuestion[]
	messages?: AgentMessageRow[]
}

const status = createResource({ url: 'shop.agent.setup.get_agent_status', auto: true })
const sessions = createResource({ url: 'shop.agent.chat.list_sessions', auto: true })

const ready = computed(() => Boolean(status.data?.ready))

const sessionId = ref<string | null>(null)
const runId = ref<string | null>(null)
const messages = ref<AgentMessageRow[]>([])
const questions = ref<AgentQuestion[]>([])
const error = ref('')
const busy = ref(false)
const answering = ref(false)
const lastMessage = ref('')
const scroller = ref<HTMLElement | null>(null)

// The transcript carries the agent's system prompt, which is not for the merchant.
const visible = computed(() => messages.value.filter((message) => message.role !== 'system'))

async function send(message: string) {
	if (busy.value || answering.value) return
	lastMessage.value = message
	error.value = ''
	questions.value = []
	messages.value = [...messages.value, { role: 'user', content: message }]
	busy.value = true
	try {
		apply(await call('shop.agent.chat.send', { message, session: sessionId.value }))
		sessions.reload()
	} catch (exception) {
		error.value = readable(exception)
	} finally {
		busy.value = false
	}
}

async function answer(answers: Record<string, string>) {
	if (!runId.value) return
	answering.value = true
	error.value = ''
	try {
		apply(await call('shop.agent.chat.answer', { run: runId.value, answers }))
	} catch (exception) {
		error.value = readable(exception)
	} finally {
		answering.value = false
	}
}

function apply(run: AgentRun) {
	sessionId.value = run.session
	runId.value = run.name
	messages.value = run.messages || []
	questions.value = run.status === 'Paused' ? run.questions || [] : []
	error.value = run.status === 'Failed' ? run.error || 'The run failed.' : ''
}

function retry() {
	if (lastMessage.value) send(lastMessage.value)
}

function newChat() {
	sessionId.value = null
	runId.value = null
	messages.value = []
	questions.value = []
	error.value = ''
	lastMessage.value = ''
}

async function openSession(name: string) {
	if (busy.value || answering.value) return
	newChat()
	busy.value = true
	try {
		const data = await call('shop.agent.chat.get_session', { session: name })
		sessionId.value = data.session
		messages.value = data.messages || []
	} catch (exception) {
		error.value = readable(exception)
	} finally {
		busy.value = false
	}
}

function readable(exception: unknown) {
	const failure = exception as { messages?: string[]; message?: string }
	return failure?.messages?.[0] || failure?.message || 'Something went wrong. Try again.'
}

watch([messages, busy, questions], () => nextTick(scrollToEnd), { deep: true })

function scrollToEnd() {
	const element = scroller.value
	if (element) element.scrollTop = element.scrollHeight
}
</script>
