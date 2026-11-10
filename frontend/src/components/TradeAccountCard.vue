<template>
	<div class="rounded-lg border border-outline-gray-1 p-4">
		<h2 class="text-base font-medium text-ink-gray-8">Trade account</h2>
		<template v-if="status.is_trade">
			<dl class="mt-2 space-y-1 text-p-sm text-ink-gray-7">
				<div>Group: {{ status.customer_group }}</div>
				<div>Payment terms: {{ status.payment_terms || 'None' }}</div>
				<div>Pay on account: {{ status.allow_on_account ? 'Yes' : 'No' }}</div>
				<div v-if="status.credit_limit">Credit limit: {{ status.formatted_credit_limit }}</div>
			</dl>
			<div class="mt-3 flex gap-2">
				<Button @click="open">Edit terms</Button>
				<Button theme="red" variant="ghost" @click="confirmEnd">End trade account</Button>
			</div>
		</template>
		<template v-else>
			<p class="mt-2 text-p-sm text-ink-gray-6">
				A trade customer joins your trade group ({{ trade.data?.customer_group }}), with its prices, and can pay on
				account.
			</p>
			<Button class="mt-3" @click="open">Make trade customer</Button>
		</template>

		<Dialog
			v-model="show"
			:options="{
				title: status.is_trade ? 'Trade terms' : 'Make trade customer',
				actions: [{ label: 'Save', variant: 'solid', loading: saving, onClick: save }],
			}"
		>
			<div class="space-y-4">
				<UiPicker
					v-model="form.payment_terms"
					label="Payment terms"
					description="When the customer's invoices are due, e.g. 20th of the following month."
					:options="[{ label: 'None', value: '' }, ...termsOptions]"
				/>
				<Switch v-model="form.allow_on_account" label="Pay on account at the store" class="!w-auto" />
				<FormControl v-model.number="form.credit_limit" type="number" label="Credit limit" />
				<p class="text-p-sm text-ink-gray-5">
					Customer prices, price lists and other terms are on the Customer in Desk.
				</p>
			</div>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { Button, Dialog, FormControl, Switch, call, createResource, dialog, toast } from 'frappe-ui'

import UiPicker from '@/components/UiPicker.vue'

interface TradeStatus {
	enabled: boolean
	is_trade: boolean
	customer_group: string
	payment_terms: string | null
	allow_on_account: number
	credit_limit: number | null
	formatted_credit_limit: string | null
}

const props = defineProps<{ customer: string; status: TradeStatus }>()
const emit = defineEmits<{ updated: [] }>()

const trade = createResource({ url: 'shop.api.trade.get_trade', auto: true })
const termsOptions = computed(() =>
	(trade.data?.payment_terms_templates || []).map((name: string) => ({ label: name, value: name })),
)

const show = ref(false)
const saving = ref(false)
const form = reactive({ payment_terms: '', allow_on_account: false, credit_limit: 0 })

function open() {
	Object.assign(form, {
		// a new trade customer starts with the group's Payment Terms; an existing one keeps theirs
		payment_terms: props.status.is_trade
			? props.status.payment_terms || ''
			: props.status.payment_terms || trade.data?.payment_terms || '',
		allow_on_account: !!props.status.allow_on_account,
		credit_limit: props.status.credit_limit || 0,
	})
	show.value = true
}

async function save() {
	saving.value = true
	try {
		await call('shop.api.trade.make_trade_customer', {
			customer: props.customer,
			payment_terms: form.payment_terms || null,
			allow_on_account: form.allow_on_account ? 1 : 0,
			credit_limit: form.credit_limit || 0,
		})
		show.value = false
		toast.success('Trade terms saved')
		emit('updated')
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not save the trade terms')
	} finally {
		saving.value = false
	}
}

function confirmEnd() {
	dialog.confirm({
		title: 'End trade account',
		message: 'Move this customer back to the group new customers join, without paying on account?',
		theme: 'red',
		confirmLabel: 'End trade account',
		onConfirm: async () => {
			await call('shop.api.trade.end_trade', { customer: props.customer })
			toast.success('Trade account ended')
			emit('updated')
		},
	})
}
</script>
