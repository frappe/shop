<template>
	<div class="mx-auto max-w-5xl px-6 pb-20">
		<CatalogProductHeader
			:title="title"
			:save-label="isEdit ? 'Save' : 'Create'"
			:dirty="dirty"
			:saving="saving"
			:storefront-url="storefrontUrl"
			@save="save"
		/>

		<CatalogProductSkeleton v-if="loading" />

		<div v-else-if="loadError" class="flex flex-col items-center gap-3 py-24 text-center">
			<p class="text-p-base text-ink-red-8">Could not load this product.</p>
			<Button @click="load">Try again</Button>
		</div>

		<div v-else class="mt-6 grid items-start gap-6 lg:grid-cols-3">
			<div class="space-y-6 lg:col-span-2">
				<CatalogSection
					v-if="isLink"
					title="Item"
					description="Pick the item you already sell in ERPNext."
				>
					<CatalogItemPicker @picked="onItemPicked" />
				</CatalogSection>

				<CatalogSection title="Basics">
					<FormControl v-model="form.product_name" label="Product name" required />
					<FormControl v-if="isEdit" v-model="form.slug" label="Slug" :description="slugHint" />
					<FormControl
						v-model="form.short_description"
						label="Short description"
						description="One line shown on product cards and in search results."
					/>
					<FormControl v-model="form.description" type="textarea" :rows="6" label="Description" />
				</CatalogSection>

				<CatalogSection title="Media">
					<CatalogImageListInput v-model="form.images" />
				</CatalogSection>

				<CatalogSection
					v-if="isEdit"
					id="variants"
					class="scroll-mt-20"
					title="Variants"
					description="Sell more than one version of this product."
				>
					<CatalogVariantsPanel :product="name!" :gallery="form.images" @updated="onVariantsUpdated" />
				</CatalogSection>

				<CatalogSection
					v-else-if="isCreate"
					title="Variants"
					description="Sell more than one version of this product."
				>
					<Switch
						v-model="withOptions"
						label="This product has options (like size or colour)"
						class="!w-auto"
					/>
					<CatalogOptionsEditor v-if="withOptions" v-model="options" />
				</CatalogSection>

				<CatalogSection title="Pricing">
					<p v-if="variantPricing" class="text-sm text-ink-gray-6">
						Prices are managed per variant. Set them in the Variants card
						<template v-if="isEdit">above.</template>
						<template v-else>after the product is created.</template>
					</p>
					<template v-else>
						<div class="grid gap-4 sm:grid-cols-2">
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
								description="Shown struck through on the storefront."
							/>
						</div>
						<p v-if="discountHint" class="text-sm text-ink-green-6">{{ discountHint }}</p>
					</template>
				</CatalogSection>

				<CatalogSection title="Highlights" description="One per line, shown next to the product.">
					<FormControl
						v-model="form.highlights"
						type="textarea"
						:rows="4"
						placeholder="Dishwasher safe"
					/>
				</CatalogSection>
			</div>

			<div class="space-y-6 lg:sticky lg:top-16">
				<CatalogSection title="Status">
					<Switch v-model="form.published" label="Published" class="!w-auto" />
					<p class="text-sm text-ink-gray-6">
						Draft products stay out of the storefront until you publish them.
					</p>
				</CatalogSection>

				<CatalogSection title="Organization">
					<Autocomplete
						v-model="collectionValue"
						label="Collections"
						placeholder="Select collections"
						:options="collectionOptions"
						multiple
					/>
					<FormControl
						v-model.number="form.ranking"
						type="number"
						label="Ranking"
						description="Higher ranked products appear first."
					/>
				</CatalogSection>

				<CatalogSection v-if="!isLink" title="Inventory">
					<CatalogStockControl
						v-if="isEdit && detail"
						:item-code="detail.item"
						:stock="detail.stock"
						:has-variants="!!detail.has_variants"
						@updated="onStockUpdated"
						@show-variants="showVariants"
					/>
					<FormControl
						v-else
						v-model.number="form.opening_stock"
						type="number"
						:label="withOptions ? 'Opening stock per variant' : 'Opening stock'"
					/>
				</CatalogSection>

				<CatalogSection v-if="isEdit" title="Danger zone">
					<p class="text-sm text-ink-gray-6">
						Deleting removes the product from the storefront. The underlying item is kept.
					</p>
					<Button theme="red" class="w-full" @click="confirmDelete">
						<template #prefix><LucideTrash2 class="size-4" /></template>
						Delete product
					</Button>
				</CatalogSection>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { Autocomplete, Button, FormControl, Switch, call, dialog, toast } from 'frappe-ui'

import LucideTrash2 from '~icons/lucide/trash-2'

import CatalogImageListInput from '@/components/CatalogImageListInput.vue'
import CatalogItemPicker from '@/components/CatalogItemPicker.vue'
import CatalogOptionsEditor, { optionsError, type ProductOption } from '@/components/CatalogOptionsEditor.vue'
import CatalogProductHeader from '@/components/CatalogProductHeader.vue'
import CatalogProductSkeleton from '@/components/CatalogProductSkeleton.vue'
import CatalogSection from '@/components/CatalogSection.vue'
import CatalogStockControl from '@/components/CatalogStockControl.vue'
import CatalogVariantsPanel from '@/components/CatalogVariantsPanel.vue'

interface Option {
	label: string
	value: string
}

interface ProductDetail {
	name: string
	item: string
	slug: string
	has_variants: number
	stock: number
}

const props = defineProps<{ name?: string }>()

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!props.name)
const isLink = computed(() => !isEdit.value && route.query.mode === 'link')
const isCreate = computed(() => !isEdit.value && !isLink.value)

const loading = ref(true)
const loadError = ref(false)
const saving = ref(false)
const leaving = ref(false)
const baseline = ref('')
const detail = ref<ProductDetail | null>(null)
const collectionOptions = ref<Option[]>([])
const itemHasVariants = ref(false)
const withOptions = ref(false)
const options = ref<ProductOption[]>([{ attribute: '', values: [] }])

const form = reactive({
	item: '',
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
	collections: [] as string[],
})

const title = computed(() => {
	if (isEdit.value) return form.product_name || 'Product'
	return isLink.value ? 'Link existing item' : 'New product'
})

const storefrontUrl = computed(() =>
	isEdit.value && detail.value?.slug ? `/product/${detail.value.slug}` : undefined,
)

const slugHint = computed(() => `Storefront URL: /product/${form.slug || detail.value?.slug || ''}`)

const variantPricing = computed(() =>
	isEdit.value ? !!detail.value?.has_variants : isLink.value && itemHasVariants.value,
)

const discountHint = computed(() => {
	const price = Number(form.price)
	const compareAt = Number(form.compare_at_price)
	if (!price || !compareAt || compareAt <= price) return ''
	return `${Math.round((1 - price / compareAt) * 100)}% off the compare-at price`
})

const collectionValue = computed({
	get: () =>
		form.collections.map((name) => ({
			label: collectionOptions.value.find((option) => option.value === name)?.label || name,
			value: name,
		})),
	set: (selected: Option[]) => (form.collections = selected.map((option) => option.value)),
})

const dirty = computed(() => !loading.value && snapshot() !== baseline.value)

watch(() => props.name, load, { immediate: true })

function snapshot() {
	return JSON.stringify({ ...form, withOptions: withOptions.value, options: options.value })
}

async function load() {
	loading.value = true
	loadError.value = false
	try {
		resetForm()
		await loadCollections()
		if (isEdit.value) await loadProduct(props.name as string)
		baseline.value = snapshot()
	} catch (error) {
		loadError.value = true
	} finally {
		loading.value = false
		leaving.value = false
	}
}

function resetForm() {
	Object.assign(form, {
		item: '',
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
		collections: [],
	})
	detail.value = null
	itemHasVariants.value = false
	withOptions.value = false
	options.value = [{ attribute: '', values: [] }]
}

async function loadCollections() {
	const rows = await call('shop.api.products.get_collections')
	collectionOptions.value = rows.map((row: { name: string; title: string }) => ({
		label: row.title,
		value: row.name,
	}))
}

async function loadProduct(name: string) {
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
		collections: doc.collections || [],
	})
}

function onItemPicked(item: { label: string; value: string; hasVariants: boolean }) {
	form.item = item.value
	itemHasVariants.value = item.hasVariants
	if (!form.product_name) form.product_name = item.label
}

function onVariantsUpdated(hasVariants: boolean) {
	if (detail.value) detail.value.has_variants = hasVariants ? 1 : 0
}

function onStockUpdated(stock: number) {
	if (detail.value) detail.value.stock = stock
}

function showVariants() {
	document.getElementById('variants')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function save() {
	if (!form.product_name.trim()) {
		toast.error('Product name is required')
		return
	}
	saving.value = true
	try {
		if (isEdit.value) await saveExisting()
		else await createNew()
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not save product')
	} finally {
		saving.value = false
	}
}

async function saveExisting() {
	const doc = await call('shop.api.products.save_product', { payload: payload() })
	detail.value = doc
	form.slug = doc.slug || ''
	baseline.value = snapshot()
	toast.success('Product saved')
}

async function createNew() {
	const name = isLink.value ? await createFromItem() : await createFresh()
	baseline.value = snapshot()
	leaving.value = true
	toast.success('Product created')
	await router.replace(`/products/${encodeURIComponent(name)}`)
}

async function createFromItem() {
	if (!form.item) throw { messages: ['Select an item first'] }
	const doc = await call('shop.api.products.save_product', { payload: payload() })
	return doc.name as string
}

async function createFresh() {
	if (!form.price) throw { messages: ['Price is required'] }
	if (!withOptions.value) {
		const doc = await call('shop.api.products.create_product', {
			product_name: form.product_name,
			price: form.price,
			description: form.description,
			short_description: form.short_description,
			compare_at_price: form.compare_at_price || 0,
			opening_stock: form.opening_stock || 0,
			images: form.images,
			collections: form.collections,
			published: form.published,
		})
		return finishCreate(doc.name)
	}
	const message = optionsError(options.value)
	if (message) throw { messages: [message] }
	const result = await call('shop.api.variants.create_variant_product', {
		product_name: form.product_name,
		options: options.value,
		price: form.price,
		opening_stock: form.opening_stock || 0,
		short_description: form.short_description,
		description: form.description,
		images: form.images,
		collections: form.collections,
		published: form.published,
	})
	return finishCreate(result.product)
}

// create_product and create_variant_product take neither highlights nor ranking.
async function finishCreate(name: string) {
	if (form.highlights || form.ranking) {
		await call('shop.api.products.save_product', {
			payload: { name, highlights: form.highlights, ranking: form.ranking, published: form.published },
		})
	}
	return name
}

function payload() {
	return {
		name: isEdit.value ? props.name : undefined,
		item: isLink.value ? form.item : undefined,
		product_name: form.product_name,
		slug: form.slug || undefined,
		short_description: form.short_description,
		description: form.description,
		compare_at_price: form.compare_at_price,
		highlights: form.highlights,
		ranking: form.ranking,
		published: form.published,
		images: form.images,
		collections: form.collections,
		price: variantPricing.value ? undefined : form.price,
	}
}

function confirmDelete() {
	dialog.confirm({
		title: 'Delete product',
		message: `Remove ${form.product_name} from the storefront? The underlying item is kept.`,
		theme: 'red',
		confirmLabel: 'Delete',
		onConfirm: async () => {
			await call('shop.api.products.delete_product', { name: props.name })
			toast.success('Product deleted')
			leaving.value = true
			router.push('/products')
		},
	})
}

onBeforeRouteLeave(() => {
	if (leaving.value || !dirty.value) return true
	return new Promise<boolean>((resolve) => {
		dialog.confirm({
			title: 'Discard changes?',
			message: 'This product has unsaved changes. Leaving now discards them.',
			theme: 'red',
			confirmLabel: 'Discard changes',
			cancelLabel: 'Keep editing',
			onConfirm: () => resolve(true),
			onCancel: () => resolve(false),
		})
	})
})
</script>
