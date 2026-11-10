<template>
	<div class="rounded-lg border border-outline-gray-1 p-4">
		<div class="flex items-center justify-between gap-2">
			<h2 class="text-base font-medium text-ink-gray-8">People</h2>
			<Button size="sm" @click="openAdd">
				<template #prefix><LucidePlus class="size-3.5" /></template>
				Add person
			</Button>
		</div>
		<p class="mt-1 text-p-sm text-ink-gray-5">
			The customer's Portal Users: people who sign in to the store and buy for this customer.
		</p>
		<div v-if="!rows.length" class="mt-3 text-sm text-ink-gray-5">No one signs in for this customer yet</div>
		<div
			v-for="person in rows"
			:key="person.user"
			class="mt-3 border-t border-outline-gray-1 pt-3 first-of-type:border-t-0"
		>
			<div class="flex items-start justify-between gap-2">
				<div class="min-w-0">
					<div class="truncate text-base text-ink-gray-8">{{ person.full_name }}</div>
					<div class="truncate text-sm text-ink-gray-5">{{ person.user }}</div>
					<div class="mt-1 flex flex-wrap items-center gap-1.5 text-sm text-ink-gray-5">
						<UiStatusBadge v-if="person.staff" label="Staff login" />
						<UiStatusBadge v-else :label="person.can_sign_in ? 'Can sign in' : 'Sign-in off'" />
						<span>{{ person.last_login ? `Last signed in ${formatDate(person.last_login)}` : 'Never signed in' }}</span>
					</div>
				</div>
				<Dropdown :options="actions(person)">
					<Button variant="ghost" :label="`Actions for ${person.full_name}`" :loading="busy === person.user">
						<template #icon><LucideEllipsisVertical class="size-4" /></template>
					</Button>
				</Dropdown>
			</div>
		</div>

		<Dialog
			v-model="showAdd"
			:options="{
				title: 'Add person',
				actions: [{ label: 'Add', variant: 'solid', loading: adding, onClick: add }],
			}"
		>
			<div class="space-y-3">
				<FormControl v-model="form.full_name" label="Name" required />
				<FormControl v-model="form.email" type="email" label="Email" required />
				<p class="text-p-sm text-ink-gray-5">
					They're emailed a link to set their password, then sign in to the store and buy for this
					customer, with its prices and terms.
				</p>
			</div>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Button, Dialog, Dropdown, FormControl, call, dialog, toast } from 'frappe-ui'

import LucideEllipsisVertical from '~icons/lucide/ellipsis-vertical'
import LucidePlus from '~icons/lucide/plus'

import UiStatusBadge from '@/components/UiStatusBadge.vue'
import { formatDate } from '@/utils/format'

type Person = {
	user: string
	full_name: string
	can_sign_in: boolean
	staff: boolean
	last_login: string | null
}

const props = defineProps<{ customer: string; people: Person[] }>()

const rows = ref<Person[]>([...props.people])
watch(
	() => props.people,
	(value) => (rows.value = [...value]),
)

const showAdd = ref(false)
const adding = ref(false)
const busy = ref('')
const form = reactive({ full_name: '', email: '' })

function openAdd() {
	Object.assign(form, { full_name: '', email: '' })
	showAdd.value = true
}

function errorMessage(error: unknown, fallback: string) {
	return (error as { messages?: string[] }).messages?.[0] || fallback
}

async function add() {
	if (adding.value) return
	adding.value = true
	try {
		rows.value = await call('shop.api.customers.add_person', {
			customer: props.customer,
			full_name: form.full_name,
			email: form.email,
		})
		showAdd.value = false
		toast.success(`${form.email} can now buy for this customer. If they had no store login, they've been emailed a link to set a password.`)
	} catch (error) {
		toast.error(errorMessage(error, 'Could not add the person'))
	} finally {
		adding.value = false
	}
}

async function run(person: Person, method: string, params: Record<string, unknown>, success: string) {
	if (busy.value) return
	busy.value = person.user
	try {
		const result = await call(`shop.api.customers.${method}`, { customer: props.customer, user: person.user, ...params })
		if (Array.isArray(result)) rows.value = result
		toast.success(success)
	} catch (error) {
		toast.error(errorMessage(error, 'Could not update the person'))
	} finally {
		busy.value = ''
	}
}

function confirmRemove(person: Person) {
	dialog.confirm({
		title: `Remove ${person.full_name}?`,
		message: 'They will no longer buy for this customer. Their login stays, with any other accounts it has.',
		onConfirm: () => run(person, 'remove_person', {}, `${person.user} removed`),
	})
}

function actions(person: Person) {
	const items = []
	if (!person.staff) {
		if (person.can_sign_in) {
			items.push({
				label: 'Send password reset link',
				onClick: () => run(person, 'send_password_reset', {}, `Password reset link sent to ${person.user}`),
			})
		}
		items.push({
			label: person.can_sign_in ? 'Turn sign-in off' : 'Turn sign-in on',
			onClick: () =>
				run(
					person,
					'set_sign_in',
					{ enabled: person.can_sign_in ? 0 : 1 },
					person.can_sign_in ? `${person.user} can no longer sign in` : `${person.user} can sign in again`,
				),
		})
	}
	items.push({ label: 'Remove from this customer', onClick: () => confirmRemove(person) })
	return items
}
</script>
