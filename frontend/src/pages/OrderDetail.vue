<template>
	<div class="mx-auto max-w-4xl px-6 py-8">
		<router-link to="/orders" class="text-sm text-ink-gray-5 hover:text-ink-gray-8">
			&larr; Orders
		</router-link>

		<div v-if="doc" class="mt-3">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<h1 class="text-xl font-semibold text-ink-gray-9">{{ doc.name }}</h1>
					<OrderStatusBadge :status="doc.status" />
				</div>
				<div class="flex items-center gap-2">
					<Button :link="`/app/sales-order/${doc.name}`">Open in Desk</Button>
					<Button theme="red" :disabled="doc.docstatus !== 1" @click="showCancelDialog = true">
						Cancel order
					</Button>
				</div>
			</div>

			<div class="mt-6 rounded-lg border border-outline-gray-1 p-4">
				<h2 class="text-base font-medium text-ink-gray-8">Customer</h2>
				<div class="mt-2 text-base text-ink-gray-7">{{ doc.customer_name }}</div>
				<div v-if="doc.contact_email" class="text-base text-ink-gray-6">{{ doc.contact_email }}</div>
				<div v-if="doc.address" class="mt-2 text-sm text-ink-gray-6" v-html="doc.address" />
			</div>

			<div class="mt-6 overflow-hidden rounded-lg border border-outline-gray-1">
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
					<tfoot>
						<tr class="border-t border-outline-gray-1">
							<td colspan="3" class="px-3 py-2 text-right font-medium text-ink-gray-8">Grand total</td>
							<td class="px-3 py-2 text-right font-semibold text-ink-gray-9">
								{{ doc.formatted_grand_total }}
							</td>
						</tr>
					</tfoot>
				</table>
			</div>
		</div>

		<Dialog
			v-model="showCancelDialog"
			:options="{
				title: 'Cancel order',
				actions: [
					{
						label: 'Cancel order',
						theme: 'red',
						variant: 'solid',
						onClick: cancelOrder,
					},
				],
			}"
		>
			<p class="text-base text-ink-gray-7">
				This will cancel {{ name }} in ERPNext. This action cannot be undone.
			</p>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Dialog, call, createResource, toast } from 'frappe-ui'

import OrderStatusBadge from '@/components/OrderStatusBadge.vue'

const props = defineProps<{ name: string }>()

const showCancelDialog = ref(false)

const order = createResource({
	url: 'shop.api.admin.get_order',
	makeParams: () => ({ name: props.name }),
	auto: true,
})

const doc = computed(() => order.data)

async function cancelOrder() {
	try {
		await call('shop.api.admin.cancel_order', { name: props.name })
		toast.success('Order cancelled')
		order.reload()
	} catch (error) {
		toast.error('Could not cancel order')
	} finally {
		showCancelDialog.value = false
	}
}
</script>
