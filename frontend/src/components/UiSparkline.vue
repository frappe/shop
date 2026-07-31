<template>
	<div class="relative" @mouseleave="hovered = null">
		<div
			v-if="hoveredPoint"
			class="pointer-events-none absolute top-0 z-10 whitespace-nowrap rounded bg-surface-gray-7 px-2 py-1 text-xs text-ink-white"
			:style="tooltipStyle"
		>
			{{ hoveredPoint.date }} &middot; {{ hoveredPoint.formatted_revenue }} &middot;
			{{ hoveredPoint.orders }}
			{{ hoveredPoint.orders === 1 ? 'order' : 'orders' }}
		</div>
		<svg :viewBox="`0 0 100 ${chartHeight}`" preserveAspectRatio="none" class="block h-36 w-full">
			<line
				v-for="line in gridLines"
				:key="line"
				x1="0"
				x2="100"
				:y1="line"
				:y2="line"
				style="stroke: var(--outline-gray-1)"
				vector-effect="non-scaling-stroke"
			/>
			<rect
				v-for="bar in bars"
				:key="bar.index"
				:x="bar.x"
				:y="bar.y"
				:width="barWidth"
				:height="bar.height"
				:class="hovered === bar.index ? 'fill-surface-gray-7' : 'fill-surface-gray-5'"
			/>
			<line
				:y1="chartHeight"
				:y2="chartHeight"
				x1="0"
				x2="100"
				style="stroke: var(--outline-gray-2)"
				vector-effect="non-scaling-stroke"
			/>
			<rect
				v-for="bar in bars"
				:key="`hover-${bar.index}`"
				:x="bar.index * slotWidth"
				y="0"
				:width="slotWidth"
				:height="chartHeight"
				fill="transparent"
				@mouseenter="hovered = bar.index"
			/>
		</svg>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

export interface SparklinePoint {
	date: string
	revenue: number
	formatted_revenue: string
	orders: number
}

const props = defineProps<{ series: SparklinePoint[] }>()

const chartHeight = 40
const plotHeight = 36
const hovered = ref<number | null>(null)

const slotWidth = computed(() => 100 / Math.max(props.series.length, 1))
const barWidth = computed(() => slotWidth.value * 0.7)
const maxRevenue = computed(() => Math.max(...props.series.map((point) => point.revenue), 1))

const bars = computed(() =>
	props.series.map((point, index) => {
		const height = (point.revenue / maxRevenue.value) * plotHeight
		return {
			index,
			x: index * slotWidth.value + slotWidth.value * 0.15,
			y: chartHeight - height,
			height,
		}
	}),
)

const gridLines = [0.25, 0.5, 0.75].map((fraction) => chartHeight - plotHeight * fraction)

const hoveredPoint = computed(() =>
	hovered.value === null ? null : props.series[hovered.value],
)
const tooltipStyle = computed(() => {
	if (hovered.value === null) return {}
	const center = (hovered.value + 0.5) * slotWidth.value
	if (center < 12) return { left: '0%', transform: 'translateY(-100%)' }
	if (center > 88) return { right: '0%', transform: 'translateY(-100%)' }
	return { left: `${center}%`, transform: 'translate(-50%, -100%)' }
})
</script>
