<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<div v-if="doc">
			<UiPageHeader :title="doc.customer_name" back-to="/customers" back-label="Customers">
				<template #actions>
					<Button :link="`/app/customer/${doc.name}`">Open in Desk</Button>
				</template>
			</UiPageHeader>

			<div class="mt-6 grid gap-6 lg:grid-cols-3">
				<div class="lg:col-span-2">
					<h2 class="mb-3 text-lg font-medium text-ink-gray-8">Orders</h2>
					<UiDataTable
						:columns="orderColumns"
						:rows="doc.orders"
						row-key="name"
						clickable
						@row-click="(row) => router.push(`/orders/${row.name}`)"
					>
						<template #cell-name="{ row }">
							<span class="font-medium text-ink-gray-8">{{ row.name }}</span>
						</template>
						<template #cell-status="{ row }">
							<UiStatusBadge :label="row.status" />
						</template>
						<template #empty>
							<UiEmptyState :icon="LucideShoppingCart" title="No orders yet" />
						</template>
					</UiDataTable>
				</div>

				<div class="space-y-6">
					<div class="rounded-lg border border-outline-gray-1 p-4">
						<h2 class="text-base font-medium text-ink-gray-8">Profile</h2>
						<div v-if="doc.email" class="mt-2 break-words text-p-base text-ink-gray-7">{{ doc.email }}</div>
						<div class="mt-1 text-sm text-ink-gray-5">Joined {{ formatDate(doc.joined) }}</div>
						<div class="mt-4 border-t border-outline-gray-1 pt-3">
							<div class="text-sm text-ink-gray-5">Lifetime spend</div>
							<div class="mt-0.5 text-xl font-semibold text-ink-gray-9">
								{{ doc.formatted_spent }}
							</div>
						</div>
					</div>

					<div class="rounded-lg border border-outline-gray-1 p-4">
						<h2 class="text-base font-medium text-ink-gray-8">Addresses</h2>
						<div v-if="!doc.addresses.length" class="mt-2 text-sm text-ink-gray-5">
							No addresses on file
						</div>
						<div
							v-for="address in doc.addresses"
							:key="address.name"
							class="mt-2 border-t border-outline-gray-1 pt-2 text-p-sm text-ink-gray-6 first:border-t-0 first:pt-0"
							v-html="address.display"
						/>
					</div>

					<div class="rounded-lg border border-outline-gray-1 p-4">
						<h2 class="text-base font-medium text-ink-gray-8">Reviews</h2>
						<div v-if="!doc.reviews.length" class="mt-2 text-sm text-ink-gray-5">
							No reviews yet
						</div>
						<div
							v-for="review in doc.reviews"
							:key="`${review.product}-${review.creation}`"
							class="mt-3 border-t border-outline-gray-1 pt-3 first:mt-2 first:border-t-0 first:pt-0"
						>
							<div class="flex items-center gap-0.5">
								<LucideStar
									v-for="starIndex in 5"
									:key="starIndex"
									class="size-3.5"
									:class="
										starIndex <= review.rating
											? 'fill-surface-gray-7 text-ink-gray-7'
											: 'text-ink-gray-3'
									"
								/>
							</div>
							<div v-if="review.title" class="mt-1 text-base text-ink-gray-8">
								{{ review.title }}
							</div>
							<div class="mt-0.5 text-sm text-ink-gray-5">
								{{ review.product }} &middot; {{ formatDate(review.creation) }}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<div v-else class="flex justify-center py-20">
			<Spinner class="size-5" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Spinner, createResource, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'

import LucideShoppingCart from '~icons/lucide/shopping-cart'
import LucideStar from '~icons/lucide/star'

import UiDataTable from '@/components/UiDataTable.vue'
import UiEmptyState from '@/components/UiEmptyState.vue'
import UiPageHeader from '@/components/UiPageHeader.vue'
import UiStatusBadge from '@/components/UiStatusBadge.vue'
import { formatDate } from '@/utils/format'

const props = defineProps<{ name: string }>()

const router = useRouter()

const customer = createResource({
	url: 'shop.api.customers.get_customer',
	makeParams: () => ({ name: props.name }),
	auto: true,
	onError: () => toast.error('Could not load customer'),
})

const doc = computed(() => customer.data)

const orderColumns = [
	{ key: 'name', label: 'Order' },
	{ key: 'transaction_date', label: 'Date', format: formatDate },
	{ key: 'status', label: 'Status' },
	{ key: 'formatted_total', label: 'Total', align: 'right' as const },
]
</script>
