"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertCircle, CheckCircle2, TrendingUp, Calendar } from "lucide-react"
import FileUploader from "@/components/file-uploader"
import ForecastResults from "@/components/forecast-results"

export default function Home() {
  const [uploadedData, setUploadedData] = useState<any>(null)
  const [forecastMonths, setForecastMonths] = useState(3)
  const [selectedModel, setSelectedModel] = useState<string>("v0")
  const [forceV0, setForceV0] = useState<boolean>(false)
  const [isLoading, setIsLoading] = useState(false)
  const [forecastResults, setForecastResults] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedEndDate, setSelectedEndDate] = useState<string>("")
  const [loadingProgress, setLoadingProgress] = useState<string>("")

  const handleFileUpload = (data: any) => {
    setUploadedData(data)
    setError(null)
    setForecastResults(null)
    if (data.meses && data.meses.length > 0) {
      setSelectedEndDate(data.meses[data.meses.length - 1])
    }
  }

  const handleGenerateForecast = async () => {
    if (!uploadedData) {
      setError("Por favor, sube un archivo primero")
      return
    }

    if (!selectedEndDate) {
      setError("Por favor, selecciona la fecha de corte")
      return
    }

    setIsLoading(true)
    setLoadingProgress("Enviando datos...")
    setError(null)

    try {
      setLoadingProgress("Procesando forecast (esto puede tomar unos momentos)...")
      const response = await fetch("/api/forecast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          salesData: uploadedData,
          forecastMonths,
          endDate: selectedEndDate,
          model: forceV0 ? "v0" : selectedModel,
          options: {},
        }),
      })

      const result = await response.json()
      if (!response.ok) throw new Error(result.error || "Error en forecast")

      setLoadingProgress("")
      setForecastResults(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido")
      setLoadingProgress("")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="w-8 h-8 text-blue-400" />
            <h1 className="text-4xl font-bold text-white">Sales Forecast Pro</h1>
          </div>
          <p className="text-slate-300">
            Análisis de ventas avanzado con forecasting inteligente y consideración de temporalidad
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Panel izquierdo - Upload y configuración */}
          <div className="lg:col-span-1 space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">Paso 1: Cargar datos</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <FileUploader onFileUpload={handleFileUpload} />

                {uploadedData && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 p-3 bg-green-900/30 rounded-lg border border-green-700/50">
                      <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
                      <span className="text-sm text-green-300">
                        {uploadedData.clientes?.length || 0} clientes + {uploadedData.totalSkus || 0} SKUs
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">Meses históricos: {uploadedData.meses?.length || 0}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">Paso 2: Configurar forecast</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    <Calendar className="w-4 h-4 inline mr-2" />
                    Fecha de corte (último mes a analizar)
                  </label>
                  <select
                    value={selectedEndDate}
                    onChange={(e) => setSelectedEndDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-slate-300 text-sm"
                  >
                    <option value="">Seleccionar mes...</option>
                    {uploadedData?.meses?.map((mes: string) => (
                      <option key={mes} value={mes}>
                        {mes}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Seleccionar modelo</label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-slate-300 text-sm"
                  >
                    <option value="v0">Automático (v0 - heurístico actual)</option>
                    <option value="holtwinters">Holt-Winters</option>
                    <option value="prophet">Prophet (requiere servicio Python)</option>
                    <option value="sarimax">SARIMAX (requiere servicio Python)</option>
                    <option value="ml_cluster">ML por clúster (XGBoost/LightGBM)</option>
                  </select>
                  <p className="text-xs text-slate-400 mt-2">Nota: algunos modelos requieren un servicio externo; si no hay servicio disponible, el sistema hará fallback automático al algoritmo local (v0).</p>

                  <div className="mt-3 flex items-center gap-2">
                    <input
                      id="force-v0"
                      type="checkbox"
                      checked={forceV0}
                      onChange={(e) => setForceV0(e.target.checked)}
                      className="w-4 h-4"
                    />
                    <label htmlFor="force-v0" className="text-xs text-slate-300">Forzar uso de v0 (ignorar servicio externo)</label>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Meses a pronosticar: {forecastMonths}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="24"
                    value={forecastMonths}
                    onChange={(e) => setForecastMonths(Number.parseInt(e.target.value))}
                    className="w-full"
                  />
                  <p className="text-xs text-slate-400 mt-2">Entre 1 y 24 meses</p>
                </div>

                <Button
                  onClick={handleGenerateForecast}
                  disabled={!uploadedData || !selectedEndDate || isLoading}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  {isLoading ? "Generando..." : "Generar Forecast"}
                </Button>
              </CardContent>
            </Card>

            {/* Metrics */}
            {forecastResults && (
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white text-sm">Métricas</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <p className="text-xs text-slate-400">Clientes activos</p>
                    <p className="text-2xl font-bold text-blue-400">{forecastResults.metricas?.clientesActivos || 0}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">SKUs activos</p>
                    <p className="text-2xl font-bold text-purple-400">{forecastResults.metricas?.skusActivos || 0}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Venta total esperada</p>
                    <p className="text-2xl font-bold text-green-400">
                      €
                      {(forecastResults.metricas?.ventaTotal || 0).toLocaleString("es-ES", {
                        maximumFractionDigits: 0,
                      })}
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            </div>

          <div className="lg:col-span-2">
            {error && (
              <Card className="bg-red-900/30 border-red-700/50 mb-6">
                <CardContent className="flex items-center gap-3 p-4">
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                  <p className="text-red-300">{error}</p>
                </CardContent>
              </Card>
            )}

            {isLoading && (
              <Card className="bg-blue-900/30 border-blue-700/50 mb-6">
                <CardContent className="flex items-center gap-3 p-4">
                  <div className="animate-spin">
                    <TrendingUp className="w-5 h-5 text-blue-400" />
                  </div>
                  <p className="text-blue-300">{loadingProgress || "Procesando..."}</p>
                </CardContent>
              </Card>
            )}

            {forecastResults && <ForecastResults data={forecastResults} />}

            {!forecastResults && !error && !isLoading && (
              <Card className="bg-slate-800 border-slate-700 h-96 flex items-center justify-center">
                <div className="text-center">
                  <TrendingUp className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                  <p className="text-slate-400">Carga un archivo y genera el forecast</p>
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </main>
  )
}
