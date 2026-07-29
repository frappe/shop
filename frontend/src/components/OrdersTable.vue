<template>
	<div class="overflow-hidden rounded-lg border border-outline-gray-1">
		<table class="w-full text-base">
			<thead>
				<tr class="border-b border-outline-gray-1 text-left text-sm text-ink-gray-5">
					<th class="px-3 py-2 font-normal">Order</th>
					<th class="px-3 py-2 font-normal">Customer</th>
					<th class="px-3 py-2 font-normal">Date</th>
					<th class="px-3 py-2 font-normal">Status</th>
					<th class="px-3 py-2 text-right font-normal">Total</th>
				</tr>
			</thead>
			<tbody>
				<tr
					v-for="order in orders"
					:key="order.name"
					class="cursor-pointer border-b border-outline-gray-1 last:border-b-0 hover:bg-surface-gray-1"
					@click="router.push(`/orders/${order.name}`)"
				>
					<td class="px-3 py-2 font-medium text-ink-gray-8">{{ order.name }}</td>
					<td class="px-3 py-2 text-ink-gray-7">{{ order.customer_name }}</td>
					<td class="px-3 py-2 text-ink-gray-6">{{ order.transaction_date }}</td>
					<td class="px-3 py-2"><OrderStatusBadge :status="order.status" /></td>
					<td class="px-3 py-2 text-right text-ink-gray-8">{{ order.formatted_total }}</td>
				</tr>
				<tr v-if="!orders.length">
					<td colspan="5" class="px-3 py-8 text-center text-ink-gray-5">No orders yet</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

import OrderStatusBadge from '@/components/OrderStatusBadge.vue'

export interface OrderRow {
	name: string
	customer_name: string
	transaction_date: string
	status: string
	grand_total: number
	formatted_total: string
	docstatus: number
}

defineProps<{ orders: OrderRow[] }>()

const router = useRouter()
</script>
