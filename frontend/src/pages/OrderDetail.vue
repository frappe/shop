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
						:order="doc.name"
						:docstatus="doc.docstatus"
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
					</div>

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

		<Dialog v-model="showConfirm" :options="dialogOptions">
			<template #body-content>
				<p class="text-p-base text-ink-gray-7">{{ pending?.message }}</p>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Dialog, Spinner, call, createResource, toast } from 'frappe-ui'

import FulfillmentPanel from '@/components/FulfillmentPanel.vue'
import UiPageHeader from '@/components/UiPageHeader.vue'
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

const canMarkPaid = computed(() => doc.value.docstatus === 1 && doc.value.payment_status !== 'Paid')
const canFulfill = computed(
	() =>
		doc.value.docstatus === 1 &&
		!['Fulfilled', 'Cancelled'].includes(doc.value.fulfillment_status),
)
const canCancel = computed(() => doc.value.docstatus !== 2)

const actions = {
	markPaid: {
		title: 'Mark as paid',
		message: `Record a payment entry for ${props.name}?`,
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
		message: `This will cancel ${props.name}. This action cannot be undone.`,
		buttonLabel: 'Cancel order',
		theme: 'red',
		method: 'shop.api.orders.cancel_order',
		success: 'Order cancelled',
		failure: 'Could not cancel order',
	},
} as const

type ActionKey = keyof typeof actions

const showConfirm = ref(false)
const pending = ref<(typeof actions)[ActionKey] | null>(null)

function confirmAction(key: ActionKey) {
	pending.value = actions[key]
	showConfirm.value = true
}

const dialogOptions = computed(() => ({
	title: pending.value?.title,
	actions: [
		{
			label: pending.value?.buttonLabel,
			theme: pending.value?.theme,
			variant: 'solid',
			onClick: runPending,
		},
	],
}))

async function runPending() {
	if (!pending.value) return
	try {
		await call(pending.value.method, { name: props.name })
		toast.success(pending.value.success)
		order.reload()
	} catch (error) {
		toast.error(pending.value.failure)
	} finally {
		showConfirm.value = false
	}
}
</script>
