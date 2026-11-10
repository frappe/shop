<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<div v-if="doc">
			<UiPageHeader :title="doc.name" back-to="/orders" back-label="Orders">
				<template #badges>
					<UiStatusBadge :label="doc.display_status" />
					<UiStatusBadge :label="doc.payment_status" />
					<UiStatusBadge :label="doc.fulfillment_status" />
				</template>
				<template #actions>
					<Button :link="`/app/sales-order/${doc.name}`">Open in Desk</Button>
					<Button v-if="canMarkPaid" @click="confirmAction('markPaid')">Mark paid</Button>
					<Button v-if="canFulfill" variant="solid" @click="confirmAction('fulfill')">
						Fulfill
					</Button>
					<Button v-if="canCancel" theme="red" @click="confirmAction('cancel')">Cancel</Button>
				</template>
			</UiPageHeader>

			<div class="mt-6 grid gap-6 lg:grid-cols-3">
				<div class="space-y-6 lg:col-span-2">
					<div class="overflow-hidden rounded-lg border border-outline-gray-1">
						<table class="w-full text-base">
							<thead>
								<tr class="border-b border-outline-gray-1 text-left text-sm text-ink-gray-5">
									<th class="px-3 py-2 font-normal">Item</th>
									<th class="px-3 py-2 text-right font-normal">Qty</th>
									<th class="px-3 py-2 text-right font-normal">Rate</th>
									<th class="px-3 py-2 text-right font-normal">Amount</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="item in doc.items"
									:key="item.item_code"
									class="border-b border-outline-gray-1 last:border-b-0"
								>
									<td class="px-3 py-2 text-ink-gray-8">{{ item.item_name }}</td>
									<td class="px-3 py-2 text-right text-ink-gray-7">{{ item.qty }}</td>
									<td class="px-3 py-2 text-right text-ink-gray-7">{{ item.formatted_rate }}</td>
									<td class="px-3 py-2 text-right text-ink-gray-8">{{ item.formatted_amount }}</td>
								</tr>
							</tbody>
							<tfoot class="border-t border-outline-gray-1 text-base">
								<tr>
									<td colspan="3" class="px-3 pt-3 text-right text-ink-gray-6">Subtotal</td>
									<td class="px-3 pt-3 text-right text-ink-gray-8">{{ doc.formatted_total }}</td>
								</tr>
								<tr v-if="doc.formatted_discount">
									<td colspan="3" class="px-3 pt-1 text-right text-ink-gray-6">Discount</td>
									<td class="px-3 pt-1 text-right text-ink-gray-8">
										-{{ doc.formatted_discount }}
									</td>
								</tr>
								<tr>
									<td colspan="3" class="px-3 py-3 text-right font-medium text-ink-gray-8">
										Grand total
									</td>
									<td class="px-3 py-3 text-right font-semibold text-ink-gray-9">
										{{ doc.formatted_grand_total }}
									</td>
								</tr>
							</tfoot>
						</table>
					</div>

					<FulfillmentPanel
						:key="panelVersion"
						:order="doc.name"
						:docstatus="doc.display_status === 'Cancelled' ? 2 : doc.docstatus"
						@changed="order.reload()"
					/>
				</div>

				<div class="space-y-6">
					<div class="rounded-lg border border-outline-gray-1 p-4">
						<h2 class="text-base font-medium text-ink-gray-8">Customer</h2>
						<router-link
							v-if="doc.customer"
							:to="`/customers/${doc.customer}`"
							class="mt-2 block text-base text-ink-gray-8 hover:underline"
						>
							{{ doc.customer_name }}
						</router-link>
						<div v-if="doc.contact_email" class="text-base text-ink-gray-6">
							{{ doc.contact_email }}
						</div>
						<div v-if="doc.address" class="mt-2 text-p-sm text-ink-gray-6" v-html="doc.address" />
						<div v-if="doc.po_no" class="mt-2 text-p-sm text-ink-gray-6">
							Purchase order: <span class="text-ink-gray-8">{{ doc.po_no }}</span>
						</div>
						<div v-if="doc.order_note" class="mt-2 whitespace-pre-line text-p-sm text-ink-gray-8">
							<span class="text-ink-gray-6">Customer's note:</span> {{ doc.order_note }}
						</div>
					</div>

					<ReturnsPanel :order="doc.name" />
					<section
						v-if="doc.refunds_due?.length"
						class="rounded-lg border border-outline-gray-1 p-4"
					>
						<h2 class="text-base font-medium text-ink-gray-8">Refunds due</h2>
						<p class="mt-1 text-p-sm text-ink-gray-5">
							Nothing is paid back until you refund it here.
						</p>
						<ul class="mt-3 divide-y divide-outline-gray-1">
							<li
								v-for="due in doc.refunds_due"
								:key="due.credit_note"
								class="flex flex-wrap items-center justify-between gap-2 py-3"
							>
								<span class="text-base text-ink-gray-8">
									{{ due.formatted_amount }} · credit note {{ due.credit_note }}
								</span>
								<span class="flex gap-2">
									<Button v-if="due.online" @click="openRefund(due, 'card')">
										Refund via {{ due.gateway || 'payment gateway' }}
									</Button>
									<Button @click="openRefund(due, 'bank')">Refund from bank</Button>
								</span>
							</li>
						</ul>
					</section>

					<div class="rounded-lg border border-outline-gray-1 p-4">
						<h2 class="text-base font-medium text-ink-gray-8">Timeline</h2>
						<ol class="mt-3">
							<li
								v-for="(event, index) in doc.timeline"
								:key="index"
								class="relative border-l border-outline-gray-2 pb-4 pl-4 last:border-transparent last:pb-0"
							>
								<span
									class="absolute -left-[4.5px] top-1 size-2 rounded-full bg-surface-gray-6"
								/>
								<div class="text-base text-ink-gray-8">{{ event.label }}</div>
								<div class="text-sm text-ink-gray-5">{{ formatDateTime(event.on) }}</div>
							</li>
						</ol>
					</div>
				</div>
			</div>
		</div>

		<div v-else class="flex justify-center py-20">
			<Spinner class="size-5" />
		</div>

		<Dialog v-model="showRefund" :options="refundOptions">
			<template #body-content>
				<p class="text-p-base text-ink-gray-7">
					{{
						refund.how === 'card'
							? `Refund ${refund.due?.formatted_amount} the way the customer paid (${refund.due?.gateway || 'payment gateway'})? This sends the money now.`
							: `Record a refund of ${refund.due?.formatted_amount} paid from your bank account. Pay the customer from that account yourself.`
					}}
				</p>
				<UiPicker
					v-if="refund.how === 'bank'"
					v-model="refund.bank_account"
					class="mt-4"
					label="Paid from"
					description="Your bank account the refund is paid from."
					:options="bankAccountOptions"
				/>
			</template>
		</Dialog>

		<Dialog v-model="showConfirm" :options="dialogOptions">
			<template #body-content>
				<p class="text-p-base text-ink-gray-7">{{ pending?.message }}</p>
				<div v-if="pending?.method === 'shop.api.orders.mark_paid'" class="mt-4 flex flex-col gap-3">
					<UiPicker
						v-model="payment.bank_account"
						label="Paid into"
						description="Your bank account the payment arrived in."
						:options="bankAccountOptions"
					/>
					<FormControl
						v-model.number="payment.amount"
						type="number"
						:label="`Amount received (${paidCurrency})`"
						:description="`Still owed: ${doc.formatted_amount_due}`"
					/>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Dialog, FormControl, Spinner, call, createResource, toast } from 'frappe-ui'

import FulfillmentPanel from '@/components/FulfillmentPanel.vue'
import ReturnsPanel from '@/components/ReturnsPanel.vue'
import UiPageHeader from '@/components/UiPageHeader.vue'
import UiPicker from '@/components/UiPicker.vue'
import UiStatusBadge from '@/components/UiStatusBadge.vue'
import { formatDateTime } from '@/utils/format'

const props = defineProps<{ name: string }>()

const order = createResource({
	url: 'shop.api.orders.get_order',
	makeParams: () => ({ name: props.name }),
	auto: true,
	onError: () => toast.error('Could not load order'),
})

const doc = computed(() => order.data)

const isOpen = computed(() => doc.value.docstatus === 1 && doc.value.status !== 'Closed')
const canMarkPaid = computed(() => isOpen.value && doc.value.payment_status !== 'Paid')
const canFulfill = computed(
	() =>
		isOpen.value &&
		!['Preparing', 'Shipped', 'Fulfilled', 'Cancelled'].includes(doc.value.fulfillment_status),
)
const canCancel = computed(() => isOpen.value)

const actions = {
	markPaid: {
		title: 'Mark as paid',
		message: `Record the payment for ${props.name} as an ERPNext Payment Entry.`,
		buttonLabel: 'Mark paid',
		theme: 'gray',
		method: 'shop.api.orders.mark_paid',
		success: 'Order marked as paid',
		failure: 'Could not mark order as paid',
	},
	fulfill: {
		title: 'Fulfill order',
		message: `Create and submit a delivery note for ${props.name}?`,
		buttonLabel: 'Fulfill',
		theme: 'gray',
		method: 'shop.api.orders.fulfill',
		success: 'Order fulfilled',
		failure: 'Could not fulfill order',
	},
	cancel: {
		title: 'Cancel order',
		message: `Cancel ${props.name} and email the customer. An unpaid order is cancelled; a paid or invoiced one gets a credit note and is closed, and you refund it from Refunds due. This can't be undone.`,
		buttonLabel: 'Cancel order',
		theme: 'red',
		method: 'shop.api.orders.cancel_order',
		success: 'Order cancelled',
		failure: 'Could not cancel order',
	},
} as const

type ActionKey = keyof typeof actions

const showConfirm = ref(false)
// cancelling or refunding changes the shipment too, so the panel loads it again
const panelVersion = ref(0)
const pending = ref<(typeof actions)[ActionKey] | null>(null)

const payment = reactive({ bank_account: '', amount: 0 as number | null })

// what arrived is entered in the bank account's currency; the order's amount is only a guide in its own
const paidCurrency = computed(
	() =>
		doc.value?.bank_accounts?.find((account: { name: string }) => account.name === payment.bank_account)
			?.currency || doc.value?.currency,
)
watch(
	() => payment.bank_account,
	() => {
		payment.amount = paidCurrency.value === doc.value?.currency ? doc.value?.amount_due : null
	},
)

const bankAccountOptions = computed(() =>
	(doc.value?.bank_accounts || []).map((account: { name: string; currency: string }) => ({
		label: `${account.name} (${account.currency})`,
		value: account.name,
	})),
)

type RefundDue = {
	credit_note: string
	amount: number
	formatted_amount: string
	online: boolean
	gateway: string | null
}

const showRefund = ref(false)
const refund = reactive<{ due: RefundDue | null; how: 'card' | 'bank'; bank_account: string }>({
	due: null,
	how: 'card',
	bank_account: '',
})

function openRefund(due: RefundDue, how: 'card' | 'bank') {
	Object.assign(refund, { due, how, bank_account: doc.value.bank_accounts?.[0]?.name || '' })
	showRefund.value = true
}

const running = ref(false)

const refundOptions = computed(() => ({
	title: 'Refund',
	actions: [
		{
			label: 'Refund',
			variant: 'solid',
			theme: 'red',
			loading: running.value,
			disabled: refund.how === 'bank' && !refund.bank_account,
			onClick: runRefund,
		},
	],
}))

async function runRefund() {
	if (!refund.due || running.value) return
	running.value = true
	try {
		await call('shop.api.orders.refund', {
			name: props.name,
			credit_note: refund.due.credit_note,
			method: refund.how,
			bank_account: refund.how === 'bank' ? refund.bank_account : undefined,
		})
		toast.success('Refund recorded')
		order.reload()
		panelVersion.value++
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not refund')
	} finally {
		running.value = false
		showRefund.value = false
	}
}

function confirmAction(key: ActionKey) {
	pending.value = actions[key]
	if (key === 'markPaid') {
		payment.bank_account = doc.value.bank_accounts?.[0]?.name || ''
		payment.amount = doc.value.amount_due
	}
	showConfirm.value = true
}

const dialogOptions = computed(() => ({
	title: pending.value?.title,
	actions: [
		{
			label: pending.value?.buttonLabel,
			theme: pending.value?.theme,
			variant: 'solid',
			loading: running.value,
			onClick: runPending,
		},
	],
}))

async function runPending() {
	if (!pending.value || running.value) return
	running.value = true
	try {
		const extra = pending.value.method === 'shop.api.orders.mark_paid' ? { ...payment } : {}
		await call(pending.value.method, { name: props.name, ...extra })
		toast.success(pending.value.success)
		order.reload()
		panelVersion.value++
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || pending.value.failure)
	} finally {
		running.value = false
		showConfirm.value = false
	}
}
</script>
