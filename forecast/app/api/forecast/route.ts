import { type NextRequest, NextResponse } from "next/server"

function formatDateSpanish(date: Date | string): string {
  const dateObj = typeof date === "string" ? new Date(date) : date
  const day = String(dateObj.getDate()).padStart(2, "0")
  const month = String(dateObj.getMonth() + 1).padStart(2, "0")
  const year = dateObj.getFullYear()
  return `${day}/${month}/${year}`
}

function getBusinessDays(year: number, month: number): number {
  let count = 0
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  for (let d = 1; d <= daysInMonth; d++) {
    const date = new Date(year, month, d)
    const dayOfWeek = date.getDay()
    if (dayOfWeek !== 0 && dayOfWeek !== 6) count++
  }
  return count
}

function getBusinessDaysFactor(
  currentYear: number,
  currentMonth: number,
  previousYear: number,
  previousMonth: number,
): number {
  const bd_current = getBusinessDays(currentYear, currentMonth)
  const bd_previous = getBusinessDays(previousYear, previousMonth)
  return bd_previous > 0 ? bd_current / bd_previous : 1
}

function isClienteCerrado(
  ventasPorMes: Record<string, number>,
  mesesOrdenados: string[],
  endDateIdx: number,
  umbralMeses = 3,
): boolean {
  if (endDateIdx < 0) return true

  let sinCompra = 0
  for (let i = endDateIdx; i >= Math.max(0, endDateIdx - umbralMeses); i--) {
    const mes = mesesOrdenados[i]
    const venta = ventasPorMes[mes] || 0
    if (venta <= 0) {
      sinCompra++
    } else {
      sinCompra = 0
    }
  }

  return sinCompra > umbralMeses
}

function getMesInicio(ventasPorMes: Record<string, number>, mesesOrdenados: string[]): number {
  for (let i = 0; i < mesesOrdenados.length; i++) {
    if ((ventasPorMes[mesesOrdenados[i]] || 0) > 0) {
      return i
    }
  }
  return 0
}

function detectOutliers(valores: number[]): number[] {
  if (valores.length < 4) return valores

  const sorted = [...valores].sort((a, b) => a - b)
  const q1 = sorted[Math.floor(sorted.length * 0.25)]
  const q3 = sorted[Math.floor(sorted.length * 0.75)]
  const iqr = q3 - q1
  const lower = q1 - 1.5 * iqr
  const upper = q3 + 1.5 * iqr

  return valores.map((v) => {
    if (v < lower) return lower
    if (v > upper) return upper
    return v
  })
}

function calculateForecastAdvanced(
  historico: number[],
  mesesOrdenados: string[],
  endDateIdx: number,
  periodos: number,
  mesInicio: number,
): { forecast: number[]; mape: number } {
  const datosValidos = historico.slice(mesInicio, endDateIdx + 1)

  if (datosValidos.length < 2) {
    const lastVal = datosValidos.length > 0 ? datosValidos[datosValidos.length - 1] : 0
    return { forecast: Array(periodos).fill(Math.max(0, lastVal * 0.9)), mape: 999 }
  }

  const datosLimpios = detectOutliers(datosValidos)

  const n = datosLimpios.length
  const sumX = (n * (n + 1)) / 2
  const sumX2 = (n * (n + 1) * (2 * n + 1)) / 6
  const sumY = datosLimpios.reduce((a, b) => a + b, 0)
  const sumXY = datosLimpios.reduce((sum, val, i) => sum + val * (i + 1), 0)

  const denominator = n * sumX2 - sumX * sumX
  const slope = denominator !== 0 ? (n * sumXY - sumX * sumY) / denominator : 0
  const intercept = (sumY - slope * sumX) / n

  const seasonalPeriod = Math.min(12, Math.max(3, Math.floor(n / 2)))
  const seasonalFactors: number[] = []

  for (let s = 0; s < seasonalPeriod; s++) {
    const valores = []
    for (let i = s; i < datosLimpios.length; i += seasonalPeriod) {
      valores.push(datosLimpios[i])
    }
    const promedio = valores.reduce((a, b) => a + b, 0) / valores.length
    const mediaGlobal = sumY / n
    seasonalFactors[s] = mediaGlobal > 0 ? promedio / mediaGlobal : 1
  }

  const forecast: number[] = []

  for (let i = 0; i < periodos; i++) {
    const futuroPeriodo = n + i + 1
    const tendencia = Math.max(0, intercept + slope * futuroPeriodo)
    const factor = seasonalFactors[(futuroPeriodo - 1) % seasonalPeriod] || 1
    const pred = Math.max(0, tendencia * factor)
    forecast.push(pred)
  }

  let mape = 0
  if (datosLimpios.length >= 3) {
    const testSize = Math.min(3, datosLimpios.length - 1)
    let errorSum = 0
    for (let i = 0; i < testSize; i++) {
      const actual = datosLimpios[datosLimpios.length - testSize + i]
      const futuroPeriodo = n - testSize + i + 1
      const pred = intercept + slope * futuroPeriodo
      if (actual > 0) {
        errorSum += Math.abs((pred - actual) / actual)
      }
    }
    mape = (errorSum / testSize) * 100
  }

  return { forecast, mape }
}

interface SkuData {
  codigoCliente: string
  codigoArticulo: string
  skuId: string
  envaseDesc: string
  formatoDesc: string
  grupoMat: string
  grupoMatDesc: string
  marcaDesc: string
  materialId: string
  marcaDesglose: string
  negocioDesc: string
  ventasMes: Record<string, number>
}

interface ClienteData {
  codigo: string
  skus: SkuData[]
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const { salesData, forecastMonths, endDate, model = "v0", options } = await request.json()

    if (!salesData?.clientes || salesData.clientes.length === 0) {
      return NextResponse.json({ error: "No hay datos de clientes" }, { status: 400 })
    }

    // If model is not v0 and MODEL_SERVICE_URL is set, proxy to Python service
    const modelServiceUrl = process.env.MODEL_SERVICE_URL
    if (model !== "v0" && modelServiceUrl) {
      console.log(`[proxy] Forwarding ${model} request to ${modelServiceUrl}`)
      
      try {
        const response = await fetch(`${modelServiceUrl}/predict`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            salesData,
            forecastMonths,
            endDate,
            model,
            options: options || {}
          }),
          signal: AbortSignal.timeout(120000), // 2 min timeout
        })

        if (!response.ok) {
          const error = await response.json()
          console.error(`[proxy] Model service error:`, error)
          throw new Error(error.detail || "Model service error")
        }

        const result = await response.json()
        console.log(`[proxy] Model service success: ${model}`)
        return NextResponse.json(result)
        
      } catch (error) {
        console.error(`[proxy] Failed to reach model service:`, error)
        console.log(`[fallback] Running v0 algorithm instead`)
        // Fallback to v0 if service unavailable
      }
    }



    // Original v0 implementation (baseline)
    const clientes = salesData.clientes as ClienteData[]
    const meses = salesData.meses as string[]
    const mesesFecha = (salesData.mesesFecha as string[]).map((f) => new Date(f))

    if (!meses || meses.length === 0) {
      return NextResponse.json({ error: "No hay meses válidos" }, { status: 400 })
    }

    const endDateIdx = meses.indexOf(endDate)
    if (endDateIdx < 0) {
      return NextResponse.json({ error: "Fecha de corte no válida" }, { status: 400 })
    }

    console.log(
      `[v0] Iniciando forecast (requested model=${model}): ${clientes.length} clientes, ${meses.length} períodos, ${forecastMonths} meses a pronosticar`,
    )

    const forecastMeses: string[] = []
    const forecastMesesFecha: Date[] = []
    const currentDate = new Date(mesesFecha[endDateIdx])
    currentDate.setMonth(currentDate.getMonth() + 1)

    for (let i = 0; i < forecastMonths; i++) {
      const year = currentDate.getFullYear()
      const month = String(currentDate.getMonth() + 1).padStart(2, "0")
      forecastMeses.push(`${year}-${month}`)
      forecastMesesFecha.push(new Date(currentDate))
      currentDate.setMonth(currentDate.getMonth() + 1)
    }

    const resultadosPorSku: any[] = []
    const resultadosPorCliente: any[] = []
    let totalVentasHistoricas = 0
    let totalForecast = 0
    let processedCount = 0

    clientes.forEach((cliente, clienteIdx) => {
      if (clienteIdx % 500 === 0) {
        console.log(`[v0] Procesando cliente ${clienteIdx + 1}/${clientes.length}...`)
      }

      let ventasClienteHistorico = 0
      let ventasClienteForecast = 0
      let skusCerrados = 0

      cliente.skus.forEach((sku) => {
        const historico = meses.map((m) => sku.ventasMes[m] || 0)
        const mesInicio = getMesInicio(sku.ventasMes, meses)
        const cerrada = isClienteCerrado(sku.ventasMes, meses, endDateIdx, 3)

        let forecast: number[] = []
        let mape = 0

        if (!cerrada && mesInicio <= endDateIdx) {
          const result = calculateForecastAdvanced(historico, meses, endDateIdx, forecastMonths, mesInicio)
          forecast = result.forecast
          mape = result.mape
        } else {
          forecast = Array(forecastMonths).fill(0)
          if (cerrada) skusCerrados++
        }

        const ultimoValor = historico[endDateIdx] || 0
        const primerForecast = forecast.length > 0 ? forecast[0] : 0
        const variacion =
          ultimoValor > 0 && primerForecast > 0 ? ((primerForecast - ultimoValor) / ultimoValor) * 100 : 0

        resultadosPorSku.push({
          codigoCliente: cliente.codigo,
          codigoArticulo: sku.codigoArticulo,
          skuId: sku.skuId,
          grupoMateriales: sku.grupoMatDesc || sku.grupoMat,
          marca: sku.marcaDesc,
          negocio: sku.negocioDesc,
          ultimoValor,
          forecast: primerForecast,
          variacion,
          estado: cerrada ? "cerrado" : "activo",
          mape: mape > 0 ? mape : null,
          forecast_detalle: forecast,
        })

        ventasClienteHistorico += ultimoValor
        ventasClienteForecast += primerForecast
        totalVentasHistoricas += ultimoValor
        totalForecast += primerForecast
      })

      const variacionCliente =
        ventasClienteHistorico > 0
          ? ((ventasClienteForecast - ventasClienteHistorico) / ventasClienteHistorico) * 100
          : 0

      resultadosPorCliente.push({
        codigoCliente: cliente.codigo,
        ventasHistorico: ventasClienteHistorico,
        ventasForecast: ventasClienteForecast,
        variacion: variacionCliente,
        skusActivos: cliente.skus.length - skusCerrados,
      })

      processedCount++
    })

    console.log(`[v0] Forecast completado. Generando gráficos...`)

    const graficoData = meses.slice(0, endDateIdx + 1).map((mes, idx) => {
      const fecha = mesesFecha[idx]
      const year = fecha.getFullYear()
      const month = fecha.getMonth()
      const year_anterior = year - 1
      const bd_factor = getBusinessDaysFactor(year, month, year_anterior, month)

      // Sumar ventas reales históricas para este mes
      let totalVentas = 0
      clientes.forEach((cliente) => {
        cliente.skus.forEach((sku) => {
          totalVentas += sku.ventasMes[mes] || 0
        })
      })

      return {
        fecha: formatDateSpanish(fecha),
        mesAbreviado: mes,
        ventas: totalVentas,
        diasHabiles: bd_factor.toFixed(2),
      }
    })

    const forecastGrafico = forecastMeses.map((mes, idx) => {
      const fecha = forecastMesesFecha[idx]
      let totalForecastMes = 0
      resultadosPorSku.forEach((sku) => {
        totalForecastMes += sku.forecast_detalle[idx] || 0
      })
      return {
        fecha: formatDateSpanish(fecha),
        mesAbreviado: mes,
        forecast: totalForecastMes,
      }
    })

    const clientesActivos = resultadosPorCliente.filter((c) => c.skusActivos > 0).length

    const crecimientoEsperado =
      totalVentasHistoricas > 0 ? ((totalForecast - totalVentasHistoricas) / totalVentasHistoricas) * 100 : 0

    const metricas: any = {
      exitoso: true,
      totalVentasHistoricas,
      totalForecast,
      crecimientoEsperado,
      clientesActivos,
      clientesTotales: clientes.length,
      skusActivos: resultadosPorSku.filter((s) => s.estado === "activo").length,
      graficoHistorico: graficoData,
      graficoForecast: forecastGrafico,
      resultadosPorSku: resultadosPorSku.sort((a, b) => b.forecast - a.forecast).slice(0, 20),
      resultadosPorCliente: resultadosPorCliente.sort((a, b) => b.ventasForecast - a.ventasForecast),
      detalleCompleto: {
        meses,
        forecastMeses,
        resultadosPorSku,
        resultadosPorCliente,
      },
      // Modelo solicitado / usado
      modelRequested: model,
      modelUsed: model === "v0" ? "v0" : `placeholder(v0-run)`,
    }

    console.log(`[v0] Forecast exitoso. Total: €${totalForecast.toFixed(0)}`)

    return NextResponse.json(metricas)
  } catch (error) {
    console.error("[v0] Error en forecast:", error)
    return NextResponse.json(
      {
        error: `Error procesando el forecast: ${error instanceof Error ? error.message : "Error desconocido"}`,
      },
      { status: 500 },
    )
  }
}
