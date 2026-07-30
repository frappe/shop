<template>
	<Dialog v-model="show" :options="{ title, size: '3xl', actions }">
		<div v-if="loading" class="flex justify-center py-16">
			<LoadingIndicator class="size-5 text-ink-gray-5" />
		</div>
		<div v-else class="space-y-6">
			<div v-if="mode === 'link'">
				<Autocomplete
					v-model="linkItem"
					label="ERPNext item"
					placeholder="Search items by name or code"
					:options="itemOptions"
					@update:query="searchItems"
				/>
				<p class="mt-1.5 text-sm text-ink-gray-5">
					Pick an existing item to sell it on the storefront.
				</p>
			</div>

			<template v-if="mode !== 'link' || linkItem">
				<section class="space-y-4">
					<h3 class="text-sm font-semibold text-ink-gray-8">Basics</h3>
					<div class="grid grid-cols-2 gap-4">
						<FormControl v-model="form.product_name" label="Product name" required />
						<FormControl
							v-if="mode === 'edit'"
							v-model="form.slug"
							label="Slug"
							description="Storefront URL: /product/<slug>"
						/>
					</div>
					<FormControl v-model="form.short_description" label="Short description" />
					<FormControl v-model="form.description" type="textarea" :rows="4" label="Description" />
					<div class="flex items-end gap-6">
						<FormControl
							v-if="mode === 'edit'"
							v-model="form.ranking"
							type="number"
							label="Ranking"
							description="Higher ranked products appear first"
							class="w-40"
						/>
						<Switch v-model="form.published" label="Published" class="!w-auto" />
					</div>
				</section>

				<Divider />
				<section class="space-y-3">
					<h3 class="text-sm font-semibold text-ink-gray-8">Media</h3>
					<CatalogImageListInput v-model="form.images" />
				</section>

				<template v-if="mode === 'create'">
					<Divider />
					<section class="space-y-3">
						<h3 class="text-sm font-semibold text-ink-gray-8">Options</h3>
						<div class="flex">
							<Switch
								v-model="withOptions"
								label="This product has options (like size or colour)"
								class="!w-auto"
							/>
						</div>
						<CatalogOptionsEditor v-if="withOptions" v-model="options" />
					</section>
				</template>

				<Divider />
				<section class="space-y-4">
					<h3 class="text-sm font-semibold text-ink-gray-8">Pricing</h3>
					<p v-if="hasVariants" class="text-sm text-ink-gray-6">{{ variantPriceNote }}</p>
					<template v-else>
						<div class="grid grid-cols-2 gap-4">
							<FormControl
								v-model.number="form.price"
								type="number"
								:label="withOptions ? 'Price per variant' : 'Price'"
							/>
							<FormControl
								v-if="!withOptions"
								v-model.number="form.compare_at_price"
								type="number"
								label="Compare-at price"
								description="Shown struck through on the storefront"
							/>
						</div>
						<p v-if="discountHint" class="text-sm text-ink-green-3">{{ discountHint }}</p>
					</template>
					<FormControl
						v-if="mode === 'create'"
						v-model.number="form.opening_stock"
						type="number"
						:label="withOptions ? 'Opening stock per variant' : 'Opening stock'"
						class="w-40"
					/>
				</section>

				<template v-if="mode === 'edit' && editName">
					<Divider />
					<section class="space-y-3">
						<h3 class="text-sm font-semibold text-ink-gray-8">Variants</h3>
						<CatalogVariantsPanel :product="editName" @updated="onVariantsUpdated" />
					</section>
				</template>

				<template v-if="mode !== 'create'">
					<Divider />
					<section class="space-y-3">
						<h3 class="text-sm font-semibold text-ink-gray-8">Highlights</h3>
						<FormControl
							v-model="form.highlights"
							type="textarea"
							:rows="3"
							placeholder="One highlight per line"
						/>
					</section>
				</template>

				<Divider />
				<section class="space-y-3">
					<h3 class="text-sm font-semibold text-ink-gray-8">Collections</h3>
					<Autocomplete
						v-model="selectedCollections"
						placeholder="Select collections"
						:options="collectionOptions"
						multiple
					/>
				</section>

				<template v-if="mode === 'edit' && detail">
					<Divider />
					<section class="space-y-3">
						<h3 class="text-sm font-semibold text-ink-gray-8">Inventory</h3>
						<div class="flex items-center gap-3 text-sm text-ink-gray-7">
							<span>
								Stock on hand:
								<span class="font-medium text-ink-gray-9">{{ detail.stock ?? 0 }}</span>
							</span>
							<router-link
								to="/inventory"
								class="text-ink-gray-6 underline hover:text-ink-gray-8"
								@click="show = false"
							>
								Manage in Inventory
							</router-link>
						</div>
					</section>
				</template>
			</template>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Autocomplete, Dialog, Divider, FormControl, LoadingIndicator, Switch, call, toast } from 'frappe-ui'

import CatalogImageListInput from '@/components/CatalogImageListInput.vue'
import CatalogOptionsEditor, { optionsError, type ProductOption } from '@/components/CatalogOptionsEditor.vue'
import CatalogVariantsPanel from '@/components/CatalogVariantsPanel.vue'

interface Option {
	label: string
	value: string
}

interface ProductDetail {
	name: string
	item: string
	has_variants: number
	stock: number
}

const props = defineProps<{
	mode: 'create' | 'link' | 'edit'
	editName: string | null
}>()

const show = defineModel<boolean>({ required: true })
const emit = defineEmits<{ saved: [] }>()

const loading = ref(false)
const detail = ref<ProductDetail | null>(null)
const linkItem = ref<Option | null>(null)
const itemOptions = ref<Option[]>([])
const itemVariantFlags = ref<Record<string, boolean>>({})
const collectionOptions = ref<Option[]>([])
const selectedCollections = ref<Option[]>([])
const withOptions = ref(false)
const options = ref<ProductOption[]>([])
let searchTimer: ReturnType<typeof setTimeout> | null = null

const form = reactive({
	product_name: '',
	slug: '',
	short_description: '',
	description: '',
	published: true,
	ranking: 0,
	price: null as number | null,
	compare_at_price: null as number | null,
	opening_stock: 0,
	highlights: '',
	images: [] as string[],
})

const title = computed(
	() =>
		({ create: 'Add product', link: 'Link existing item', edit: 'Edit product' })[props.mode],
)

const actions = computed(() => [
	{ label: props.mode === 'edit' ? 'Save' : 'Create', variant: 'solid', onClick: save },
])

const hasVariants = computed(() => {
	if (props.mode === 'edit') return !!detail.value?.has_variants
	if (props.mode === 'link') return !!itemVariantFlags.value[linkItem.value?.value || '']
	return false
})

const variantPriceNote = computed(() =>
	props.mode === 'edit'
		? 'Prices are managed per variant. Set them in the Variants section below.'
		: 'Prices are managed per variant.',
)

const discountHint = computed(() => {
	const price = Number(form.price)
	const compareAt = Number(form.compare_at_price)
	if (!price || !compareAt || compareAt <= price) return ''
	return `${Math.round((1 - price / compareAt) * 100)}% off the compare-at price`
})

watch(show, (open) => {
	if (open) openDialog()
})

watch(linkItem, (item) => {
	if (item && !form.product_name) form.product_name = item.label
})

async function openDialog() {
	resetForm()
	await loadCollections()
	if (props.mode === 'link') searchItems('')
	if (props.mode === 'edit' && props.editName) await loadProduct(props.editName)
}

function resetForm() {
	Object.assign(form, {
		product_name: '',
		slug: '',
		short_description: '',
		description: '',
		published: true,
		ranking: 0,
		price: null,
		compare_at_price: null,
		opening_stock: 0,
		highlights: '',
		images: [],
	})
	detail.value = null
	linkItem.value = null
	selectedCollections.value = []
	withOptions.value = false
	options.value = [{ attribute: '', values: [] }]
}

function onVariantsUpdated(hasVariants: boolean) {
	if (detail.value) detail.value.has_variants = hasVariants ? 1 : 0
	emit('saved')
}

async function loadCollections() {
	const rows = await call('shop.api.products.get_collections')
	collectionOptions.value = rows.map((row: { name: string; title: string }) => ({
		label: row.title,
		value: row.name,
	}))
}

async function loadProduct(name: string) {
	loading.value = true
	try {
		const doc = await call('shop.api.products.get_product', { name })
		detail.value = doc
		Object.assign(form, {
			product_name: doc.product_name || '',
			slug: doc.slug || '',
			short_description: doc.short_description || '',
			description: doc.description || '',
			published: !!doc.published,
			ranking: doc.ranking || 0,
			price: doc.price,
			compare_at_price: doc.compare_at_price,
			highlights: doc.highlights || '',
			images: (doc.images || []).map((row: { image: string }) => row.image),
		})
		selectedCollections.value = (doc.collections || []).map((name: string) => ({
			label: collectionOptions.value.find((c) => c.value === name)?.label || name,
			value: name,
		}))
	} catch (error) {
		toast.error('Could not load product')
		show.value = false
	} finally {
		loading.value = false
	}
}

function searchItems(query: string) {
	if (searchTimer) clearTimeout(searchTimer)
	searchTimer = setTimeout(async () => {
		const items = await call('shop.api.admin.search_items', { query })
		itemVariantFlags.value = Object.fromEntries(
			items.map((item: { name: string; has_variants: number }) => [item.name, !!item.has_variants]),
		)
		itemOptions.value = items.map((item: { name: string; item_name: string }) => ({
			label: item.item_name || item.name,
			value: item.name,
		}))
	}, 250)
}

async function save() {
	if (!form.product_name.trim()) {
		toast.error('Product name is required')
		return
	}
	try {
		if (props.mode === 'create') await (withOptions.value ? createVariantProduct() : createProduct())
		else await saveProduct()
		toast.success(props.mode === 'edit' ? 'Product saved' : 'Product created')
		show.value = false
		emit('saved')
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not save product')
	}
}

async function createProduct() {
	if (!form.price) throw { messages: ['Price is required'] }
	await call('shop.api.products.create_product', {
		product_name: form.product_name,
		price: form.price,
		description: form.description,
		short_description: form.short_description,
		compare_at_price: form.compare_at_price || 0,
		opening_stock: form.opening_stock || 0,
		images: form.images,
		collections: selectedCollections.value.map((c) => c.value),
		published: form.published,
	})
}

async function createVariantProduct() {
	const message = optionsError(options.value)
	if (message) throw { messages: [message] }
	if (!form.price) throw { messages: ['Price is required'] }
	await call('shop.api.variants.create_variant_product', {
		product_name: form.product_name,
		options: options.value,
		price: form.price,
		opening_stock: form.opening_stock || 0,
		short_description: form.short_description,
		description: form.description,
		images: form.images,
		collections: selectedCollections.value.map((c) => c.value),
		published: form.published,
	})
}

async function saveProduct() {
	if (props.mode === 'link' && !linkItem.value) throw { messages: ['Select an item first'] }
	await call('shop.api.products.save_product', {
		payload: {
			name: props.mode === 'edit' ? props.editName : undefined,
			item: props.mode === 'link' ? linkItem.value?.value : undefined,
			product_name: form.product_name,
			slug: form.slug || undefined,
			short_description: form.short_description,
			description: form.description,
			compare_at_price: form.compare_at_price,
			highlights: form.highlights,
			ranking: form.ranking,
			published: form.published,
			images: form.images,
			collections: selectedCollections.value.map((c) => c.value),
			price: hasVariants.value ? undefined : form.price,
		},
	})
}
</script>
