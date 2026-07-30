<template>
	<div class="mx-auto max-w-4xl px-6 py-8">
		<div class="flex items-center justify-between">
			<h1 class="text-xl font-semibold text-ink-gray-9">Reviews</h1>
			<div v-if="reviews.data?.total" class="flex items-center gap-2 text-base text-ink-gray-7">
				<CatalogRatingStars :rating="reviews.data.average" />
				<span class="font-medium text-ink-gray-9">{{ reviews.data.average }}</span>
				<span class="text-ink-gray-5">from {{ reviews.data.total }} reviews</span>
			</div>
		</div>

		<div class="mt-6 flex items-center gap-3">
			<div class="w-64">
				<Autocomplete
					v-model="productFilter"
					placeholder="All products"
					:options="productOptions"
				/>
			</div>
			<div class="w-40">
				<FormControl v-model="ratingFilter" type="select" :options="ratingOptions" />
			</div>
		</div>

		<CatalogListState
			:loading="reviews.loading && !reviews.data"
			:error="reviews.error"
			:empty="!rows.length"
			empty-title="No reviews found"
			empty-subtitle="Customer reviews appear here once shoppers post them."
			@retry="reviews.reload()"
		/>

		<template v-if="rows.length && !reviews.error">
			<div class="mt-4 space-y-3">
				<div
					v-for="row in rows"
					:key="row.name"
					class="rounded-lg border border-outline-gray-1 p-4"
				>
					<div class="flex items-start justify-between gap-4">
						<div class="min-w-0">
							<div class="flex items-center gap-2">
								<CatalogRatingStars :rating="row.rating" />
								<span class="font-medium text-ink-gray-9">{{ row.title }}</span>
								<Badge v-if="row.verified" theme="green" size="sm">Verified</Badge>
							</div>
							<p class="mt-1.5 line-clamp-2 text-base text-ink-gray-7">{{ row.review }}</p>
							<div class="mt-2 flex items-center gap-2 text-sm text-ink-gray-5">
								<span>{{ row.reviewer_name }}</span>
								<span>on</span>
								<a
									:href="`/product/${row.product}`"
									target="_blank"
									class="text-ink-gray-6 underline hover:text-ink-gray-8"
								>
									{{ row.product_name }}
								</a>
								<span>{{ formatDate(row.posted_on) }}</span>
							</div>
						</div>
						<Button variant="ghost" theme="red" @click="confirmDelete(row)">
							<template #icon><LucideTrash2 class="size-4" /></template>
						</Button>
					</div>
				</div>
			</div>
			<CatalogPagination
				:start="start"
				:limit="PAGE_SIZE"
				:total="reviews.data?.total || 0"
				@update:start="start = $event"
			/>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Autocomplete, Badge, FormControl, call, createResource, dialog, toast } from 'frappe-ui'

import LucideTrash2 from '~icons/lucide/trash-2'

import CatalogListState from '@/components/CatalogListState.vue'
import CatalogPagination from '@/components/CatalogPagination.vue'
import CatalogRatingStars from '@/components/CatalogRatingStars.vue'

interface ReviewRow {
	name: string
	product: string
	product_name: string
	reviewer_name: string
	rating: number
	title: string
	review: string
	verified: number
	posted_on: string
}

const PAGE_SIZE = 20

const productFilter = ref<{ label: string; value: string } | null>(null)
const ratingFilter = ref('')
const start = ref(0)

const ratingOptions = [
	{ label: 'All ratings', value: '' },
	...[5, 4, 3, 2, 1].map((n) => ({ label: `${n} star${n > 1 ? 's' : ''}`, value: String(n) })),
]

const products = createResource({
	url: 'shop.api.products.get_products',
	params: { limit: 100 },
	auto: true,
})

const productOptions = computed(() => [
	{ label: 'All products', value: '' },
	...(products.data?.products || []).map((p: { name: string; product_name: string }) => ({
		label: p.product_name,
		value: p.name,
	})),
])

const reviews = createResource({
	url: 'shop.api.reviews.get_reviews',
	makeParams: () => ({
		product: productFilter.value?.value || undefined,
		rating: ratingFilter.value ? Number(ratingFilter.value) : undefined,
		start: start.value,
		limit: PAGE_SIZE,
	}),
	auto: true,
})

const rows = computed<ReviewRow[]>(() => reviews.data?.reviews || [])

watch([productFilter, ratingFilter], () => {
	start.value = 0
	reviews.reload()
})
watch(start, () => reviews.reload())

function formatDate(date: string) {
	if (!date) return ''
	return new Date(date).toLocaleDateString('en-GB', {
		day: 'numeric',
		month: 'short',
		year: 'numeric',
	})
}

function confirmDelete(row: ReviewRow) {
	dialog.confirm({
		title: 'Delete review',
		message: `Delete this review by <b>${row.reviewer_name}</b>? This cannot be undone.`,
		theme: 'red',
		confirmLabel: 'Delete',
		onConfirm: async () => {
			await call('shop.api.reviews.delete_review', { name: row.name })
			toast.success('Review deleted')
			reviews.reload()
		},
	})
}
</script>
