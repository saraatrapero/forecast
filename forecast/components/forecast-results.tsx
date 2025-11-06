"use client"

import { useState } from "react"
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown, Download } from "lucide-react"
import * as XLSX from "xlsx"

interface ForecastResultsProps {
  data: any
}

export default function ForecastResults({ data }: ForecastResultsProps) {
  const [mostrandoDetalle, setMostrandoDetalle] = useState(false)

  const {
    totalVentasHistoricas,
    totalForecast,
    crecimientoEsperado,
    clientesActivos,
    clientesTotales,
    skusActivos,
    graficoHistorico,
    graficoForecast,
    resultadosPorSku,
    resultadosPorCliente,
    detalleCompleto,
  } = data

  // Helpers seguros para formateo que manejan null/undefined
  const isNumber = (v: any) => v !== null && v !== undefined && !Number.isNaN(Number(v))

  const formatFixed = (v: any, digits = 2, fallback = "-") => {
    return isNumber(v) ? Number(v).toFixed(digits) : fallback
  }

  const formatCurrency = (v: any, digits = 0, fallback = "-") => {
    return isNumber(v) ? `€${Number(v).toLocaleString("es-ES", { maximumFractionDigits: digits })}` : fallback
  }

  const descargarExcel = () => {
    const workbook = XLSX.utils.book_new()

    // Hoja 1: Resumen por SKU (Cliente-Artículo)
    const dataSku = resultadosPorSku.map((sku: any) => {
      const row: any = {
        "Código Cliente": sku.codigoCliente,
        "Código Artículo": sku.codigoArticulo,
        "Grupo Materiales": sku.grupoMateriales,
        Marca: sku.marca,
        Negocio: sku.negocio,
        "Última Venta (€)": formatFixed(sku.ultimoValor, 2, "0.00"),
        Estado: sku.estado,
        "Variación %": formatFixed(sku.variacion, 1, "0.0"),
      }

      // Agregar columnas de forecast por mes
      detalleCompleto.forecastMeses.forEach((mes: string, idx: number) => {
        row[`Forecast ${mes}`] = formatFixed(sku.forecast_detalle?.[idx], 2, "0.00")
      })

      return row
    })

    const sheetSku = XLSX.utils.json_to_sheet(dataSku)
    XLSX.utils.book_append_sheet(workbook, sheetSku, "SKU Forecast")

    // Hoja 2: Resumen por Cliente
    const dataCliente = resultadosPorCliente.map((cli: any) => ({
      "Código Cliente": cli.codigoCliente,
      "Ventas Históricas (€)": formatFixed(cli.ventasHistorico, 2, "0.00"),
      "Forecast Total (€)": formatFixed(cli.ventasForecast, 2, "0.00"),
      "Variación %": formatFixed(cli.variacion, 1, "0.0"),
      "SKUs Activos": cli.skusActivos,
    }))

    const sheetCliente = XLSX.utils.json_to_sheet(dataCliente)
    XLSX.utils.book_append_sheet(workbook, sheetCliente, "Cliente Forecast")

    // Hoja 3: Resumen General
    const summaryData = [
      ["Métrica", "Valor"],
      ["Total Ventas Históricas (€)", formatFixed(totalVentasHistoricas, 2, "0.00")],
      ["Total Forecast (€)", formatFixed(totalForecast, 2, "0.00")],
      ["Crecimiento Esperado %", formatFixed(crecimientoEsperado, 1, "0.0")],
      ["Clientes Activos", clientesActivos],
      ["Total de Clientes", clientesTotales],
      ["SKUs Activos", skusActivos],
    ]

    const sheetSummary = XLSX.utils.aoa_to_sheet(summaryData)
    XLSX.utils.book_append_sheet(workbook, sheetSummary, "Resumen")

    XLSX.writeFile(workbook, `Forecast_${new Date().toISOString().split("T")[0]}.xlsx`)
  }

  return (
    <div className="space-y-6">
      {/* KPIs Principales */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <p className="text-xs text-slate-400 mb-1">Venta Real (Período)</p>
            <p className="text-2xl font-bold text-green-400">{formatCurrency(totalVentasHistoricas, 0)}</p>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <p className="text-xs text-slate-400 mb-1">Forecast Próximos Meses</p>
            <p className="text-2xl font-bold text-blue-400">{formatCurrency(totalForecast, 0)}</p>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <p className="text-xs text-slate-400 mb-1">Crecimiento</p>
            <div className="flex items-center gap-2">
              {crecimientoEsperado >= 0 ? (
                <TrendingUp className="w-5 h-5 text-green-400" />
              ) : (
                <TrendingDown className="w-5 h-5 text-red-400" />
              )}
              <p className={`text-2xl font-bold ${crecimientoEsperado >= 0 ? "text-green-400" : "text-red-400"}`}>
                {isNumber(crecimientoEsperado) ? `${formatFixed(crecimientoEsperado, 1)}%` : "-"}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <p className="text-xs text-slate-400 mb-1">Cartera Activa</p>
            <p className="text-2xl font-bold text-purple-400">
              {clientesActivos} / {clientesTotales}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Botón de Descarga */}
      <div className="flex gap-2">
        <Button onClick={descargarExcel} className="bg-emerald-600 hover:bg-emerald-700 flex items-center gap-2">
          <Download className="w-4 h-4" />
          Descargar Excel con Forecast
        </Button>
        <Button onClick={() => setMostrandoDetalle(!mostrandoDetalle)} variant="outline" className="border-slate-600">
          {mostrandoDetalle ? "Ocultar" : "Mostrar"} Detalle Completo
        </Button>
      </div>

      {/* Gráfico Histórico */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Histórico de Ventas (Períodos Anteriores)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={graficoHistorico}>
              <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
              <XAxis dataKey="fecha" stroke="#94a3b8" angle={-45} textAnchor="end" height={80} />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569", borderRadius: "6px" }}
                formatter={(value: any) => `€${value.toLocaleString("es-ES", { maximumFractionDigits: 0 })}`}
              />
              <Bar dataKey="ventas" fill="#10b981" name="Ventas Reales" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Gráfico Forecast */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Forecast - Próximos Períodos</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={graficoForecast}>
              <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
              <XAxis dataKey="fecha" stroke="#94a3b8" angle={-45} textAnchor="end" height={80} />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569", borderRadius: "6px" }}
                formatter={(value: any) => `€${value.toLocaleString("es-ES", { maximumFractionDigits: 0 })}`}
              />
              <Line type="monotone" dataKey="forecast" stroke="#3b82f6" strokeWidth={2} name="Forecast" />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Top SKUs */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Top 10 SKU (Cliente-Artículo) por Forecast</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {resultadosPorSku.slice(0, 10).map((sku: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-slate-700/50 rounded text-sm">
                <div>
                  <p className="font-medium text-white">
                    {sku.codigoCliente} - {sku.codigoArticulo}
                  </p>
                  <p className="text-xs text-slate-400">{sku.grupoMateriales}</p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-blue-400">€{formatFixed(sku.forecast, 0, "0")}</p>
                  <p className={`text-xs ${sku.variacion >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {isNumber(sku.variacion) && Number(sku.variacion) >= 0 ? "+" : ""}
                    {formatFixed(sku.variacion, 1, "0.0")}%
                  </p>
                  <Badge
                    className={
                      sku.estado === "activo"
                        ? "bg-green-900/50 text-green-300 text-xs mt-1"
                        : "bg-orange-900/50 text-orange-300 text-xs mt-1"
                    }
                  >
                    {sku.estado}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Detalle Completo (opcional) */}
      {mostrandoDetalle && (
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">Detalle Completo por Cliente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {resultadosPorCliente.map((cli: any, idx: number) => (
                <div key={idx} className="p-3 bg-slate-700/50 rounded text-sm">
                  <p className="font-bold text-white mb-2">{cli.codigoCliente}</p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-slate-400">Ventas Históricas</p>
                      <p className="text-green-400">{formatCurrency(cli.ventasHistorico, 0)}</p>
                    </div>
                    <div>
                      <p className="text-slate-400">Forecast</p>
                      <p className="text-blue-400">{formatCurrency(cli.ventasForecast, 0)}</p>
                    </div>
                    <div>
                      <p className="text-slate-400">Variación</p>
                      <p className={cli.variacion >= 0 ? "text-green-400" : "text-red-400"}>
                        {isNumber(cli.variacion) && Number(cli.variacion) >= 0 ? "+" : ""}
                        {formatFixed(cli.variacion, 1, "0.0")}%
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-400">SKUs Activos</p>
                      <p className="text-purple-400">{cli.skusActivos}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Insights */}
      <Card className="bg-gradient-to-r from-amber-900/20 to-orange-900/20 border-amber-700/50">
        <CardHeader>
          <CardTitle className="text-amber-300 text-sm">Análisis y Recomendaciones</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-300 space-y-2">
          <p>
            {clientesActivos / clientesTotales > 0.8
              ? "✓ Cartera saludable con alta tasa de actividad"
              : "⚠ Considerar estrategias de retención para clientes cerrados"}
          </p>
          <p>
            {isNumber(crecimientoEsperado)
              ? crecimientoEsperado >= 0
                ? `✓ Proyección de crecimiento: ${formatFixed(crecimientoEsperado, 1)}%`
                : `⚠ Proyección de contracción: ${formatFixed(crecimientoEsperado, 1)}%`
              : "Proyección no disponible"}
          </p>
          <p>
            Todos los cálculos consideran: prorrateo del mes actual, días hábiles vs año anterior, estacionalidad y
            clientes cerrados (sin compra &gt;3 meses).
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
