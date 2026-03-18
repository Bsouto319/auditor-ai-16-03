import { useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { 
  Upload, 
  FileText, 
  Trash2, 
  Printer, 
  RefreshCw, 
  AlertTriangle,
  DollarSign,
  Users,
  Building,
  Lock,
  Globe,
  Gift,
  LogOut,
  LayoutDashboard,
  List,
  Download,
  ChevronRight,
  Calendar,
  X
} from "lucide-react";

const BREAKING_NEWS = "Nexus AI v1.0 - Neural Core Active";
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

// Formatador de moeda brasileira
const formatCurrency = (value) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(value || 0);
};

// Componente Sidebar
const Sidebar = ({ activeTab, setActiveTab }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'registros', label: 'Registros', icon: FileText },
    { id: 'divergencias', label: 'Divergências', icon: AlertTriangle },
    { id: 'saidas', label: 'Saídas', icon: LogOut },
    { id: 'upload', label: 'Upload', icon: Upload },
  ];

  return (
    <aside className="sidebar" data-testid="sidebar">
      <div className="sidebar-header">
        <h1 className="sidebar-title">Nexus AI</h1>
        <span className="sidebar-subtitle">Auditoria de Insumos</span>
      </div>
      <nav className="sidebar-nav">
        {menuItems.map(item => (
          <button
            key={item.id}
            data-testid={`nav-${item.id}`}
            className={`sidebar-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => setActiveTab(item.id)}
          >
            <item.icon size={20} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
};

// Card de Estatística
const StatCard = ({ title, value, subtitle, icon: Icon, color, testId }) => (
  <div className={`stat-card stat-card-${color}`} data-testid={testId}>
    <div className="stat-card-header">
      <span className="stat-card-title">{title}</span>
      <Icon size={24} className="stat-card-icon" />
    </div>
    <div className="stat-card-value">{value}</div>
    {subtitle && <div className="stat-card-subtitle">{subtitle}</div>}
  </div>
);

// Tabela de Registros
const RegistrosTable = ({ registros, title, emptyMessage }) => (
  <div className="table-container" data-testid="registros-table">
    <table className="data-table">
      <thead>
        <tr>
          <th>UH</th>
          <th>NOME</th>
          <th>CAT.</th>
          <th>DIÁRIA</th>
          <th>CLIENTE</th>
          <th>PARTIDA</th>
        </tr>
      </thead>
      <tbody>
        {registros.length === 0 ? (
          <tr>
            <td colSpan="6" className="empty-message">
              {emptyMessage || 'Nenhum registro encontrado'}
            </td>
          </tr>
        ) : (
          registros.map((reg, idx) => (
            <tr key={idx} data-testid={`registro-row-${idx}`}>
              <td className="font-mono">{reg.uh}</td>
              <td className="text-ellipsis">{reg.nome}</td>
              <td>
                <span className={`badge badge-${reg.tipo_classificacao?.toLowerCase()}`}>
                  {reg.tipo_classificacao}
                </span>
              </td>
              <td className="font-mono">{formatCurrency(reg.diaria)}</td>
              <td className="text-ellipsis">{reg.cliente}</td>
              <td>{reg.partida}</td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  </div>
);

// Tabela de Divergências
const DivergenciasTable = ({ divergencias }) => (
  <div className="table-container" data-testid="divergencias-table">
    <div className="table-header">
      <h3>Detalhes das Divergências</h3>
      <span className="table-hint">Tarifa cobrada ≠ valor na observação</span>
    </div>
    <table className="data-table">
      <thead>
        <tr>
          <th>UH</th>
          <th>HÓSPEDE</th>
          <th>CAT.</th>
          <th>DIÁRIA</th>
          <th>OBS. VALOR</th>
          <th>DIFERENÇA</th>
        </tr>
      </thead>
      <tbody>
        {divergencias.length === 0 ? (
          <tr>
            <td colSpan="6" className="empty-message success">
              ✅ Nenhuma divergência encontrada
            </td>
          </tr>
        ) : (
          divergencias.map((div, idx) => (
            <tr key={idx} className="divergencia-row" data-testid={`divergencia-row-${idx}`}>
              <td className="font-mono">{div.uh}</td>
              <td className="text-ellipsis">{div.nome}</td>
              <td>
                <span className={`badge badge-${div.tipo_classificacao?.toLowerCase()}`}>
                  {div.tipo_classificacao}
                </span>
              </td>
              <td className="font-mono">{formatCurrency(div.diaria)}</td>
              <td className="font-mono">{formatCurrency(div.valor_observacao)}</td>
              <td className="font-mono text-danger">{formatCurrency(div.divergencia)}</td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  </div>
);

// Filtros de Categoria
const CategoryFilters = ({ activeFilter, setActiveFilter, counts }) => {
  const filters = [
    { id: 'todos', label: 'Todos', count: counts.todos },
    { id: 'faturados', label: 'Faturados', count: counts.faturados },
    { id: 'grupos', label: 'Grupos', count: counts.grupos },
    { id: 'cortesias', label: 'Cortesias', count: counts.cortesias },
    { id: 'online_b2b', label: 'Online/B2B', count: counts.online_b2b },
    { id: 'pgto_direto', label: 'Pgto Direto', count: counts.pgto_direto },
    { id: 'confidenciais', label: 'Confidenciais', count: counts.confidenciais },
  ];

  return (
    <div className="category-filters" data-testid="category-filters">
      {filters.map(filter => (
        <button
          key={filter.id}
          data-testid={`filter-${filter.id}`}
          className={`filter-btn ${activeFilter === filter.id ? 'active' : ''}`}
          onClick={() => setActiveFilter(filter.id)}
        >
          {filter.label}
          {filter.count > 0 && <span className="filter-count">{filter.count}</span>}
        </button>
      ))}
    </div>
  );
};

// Dashboard Principal
const Dashboard = ({ data, onClear, onPrint }) => {
  if (!data) {
    return (
      <div className="empty-state" data-testid="empty-dashboard">
        <Upload size={64} className="empty-icon" />
        <h2>Nenhum relatório carregado</h2>
        <p>Faça upload de um PDF para começar a auditoria</p>
      </div>
    );
  }

  const totalDivergencias = data.divergencias?.reduce((acc, d) => acc + (d.divergencia || 0), 0) || 0;

  return (
    <div className="dashboard-content" data-testid="dashboard-content">
      <div className="dashboard-header">
        <div>
          <h2>Dashboard de Auditoria</h2>
          <p className="dashboard-subtitle">
            PRE — {data.total_hospedes} hóspedes — {data.total_quartos} quartos — {data.data_relatorio}
          </p>
        </div>
        <div className="dashboard-actions">
          <button className="btn btn-danger" onClick={onClear} data-testid="btn-clear">
            <Trash2 size={18} />
            Limpar
          </button>
          <button className="btn btn-secondary" onClick={onPrint} data-testid="btn-print">
            <Printer size={18} />
            Imprimir
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard 
          title="REVENUE TOTAL" 
          value={formatCurrency(data.revenue_total)}
          subtitle={`ADR: ${formatCurrency(data.adr)}`}
          icon={DollarSign}
          color="blue"
          testId="stat-revenue"
        />
        <StatCard 
          title="FATURADOS" 
          value={data.faturados?.length || 0}
          subtitle={formatCurrency(data.faturados?.reduce((a, r) => a + r.diaria, 0))}
          icon={FileText}
          color="purple"
          testId="stat-faturados"
        />
        <StatCard 
          title="GRUPOS" 
          value={data.grupos?.length || 0}
          subtitle={formatCurrency(data.grupos?.reduce((a, r) => a + r.diaria, 0))}
          icon={Users}
          color="yellow"
          testId="stat-grupos"
        />
        <StatCard 
          title="CONFIDENCIAIS" 
          value={data.confidenciais?.length || 0}
          subtitle={formatCurrency(data.confidenciais?.reduce((a, r) => a + r.diaria, 0))}
          icon={Lock}
          color="gold"
          testId="stat-confidenciais"
        />
      </div>

      <div className="stats-grid">
        <StatCard 
          title="PGTO DIRETO" 
          value={data.pgto_direto?.length || 0}
          subtitle={formatCurrency(data.pgto_direto?.reduce((a, r) => a + r.diaria, 0))}
          icon={Building}
          color="green"
          testId="stat-pgto-direto"
        />
        <StatCard 
          title="ONLINE/B2B" 
          value={data.online_b2b?.length || 0}
          subtitle={formatCurrency(data.online_b2b?.reduce((a, r) => a + r.diaria, 0))}
          icon={Globe}
          color="teal"
          testId="stat-online-b2b"
        />
        <StatCard 
          title="CORTESIAS" 
          value={data.cortesias?.length || 0}
          subtitle={`${data.cortesias?.length || 0} quartos`}
          icon={Gift}
          color="orange"
          testId="stat-cortesias"
        />
        <StatCard 
          title="SAÍDAS" 
          value={data.saidas?.length || 0}
          subtitle="Hoje + amanhã"
          icon={LogOut}
          color="pink"
          testId="stat-saidas"
        />
      </div>

      {data.divergencias?.length > 0 && (
        <div className="alert-banner" data-testid="divergencias-alert">
          <AlertTriangle size={24} />
          <div>
            <strong>{data.divergencias.length} divergências encontradas</strong>
            <p>Diferença total: {formatCurrency(totalDivergencias)}</p>
          </div>
        </div>
      )}
    </div>
  );
};

// Página de Registros
const RegistrosPage = ({ data }) => {
  const [activeFilter, setActiveFilter] = useState('todos');

  if (!data) {
    return (
      <div className="empty-state" data-testid="registros-page-empty">
        <FileText size={64} className="empty-icon" />
        <h2>Nenhum registro</h2>
        <p>Faça upload de um PDF para ver os registros</p>
      </div>
    );
  }

  const counts = {
    todos: data.registros?.length || 0,
    faturados: data.faturados?.length || 0,
    grupos: data.grupos?.length || 0,
    cortesias: data.cortesias?.length || 0,
    online_b2b: data.online_b2b?.length || 0,
    pgto_direto: data.pgto_direto?.length || 0,
    confidenciais: data.confidenciais?.length || 0,
  };

  const getFilteredRegistros = () => {
    switch(activeFilter) {
      case 'faturados': return data.faturados || [];
      case 'grupos': return data.grupos || [];
      case 'cortesias': return data.cortesias || [];
      case 'online_b2b': return data.online_b2b || [];
      case 'pgto_direto': return data.pgto_direto || [];
      case 'confidenciais': return data.confidenciais || [];
      default: return data.registros || [];
    }
  };

  return (
    <div className="page-content" data-testid="registros-page">
      <div className="page-header">
        <div>
          <h2>Registros</h2>
          <p>{getFilteredRegistros().length} registros</p>
        </div>
        <div className="date-display" data-testid="registros-date">
          <Calendar size={18} />
          {data.data_relatorio}
        </div>
      </div>
      
      <CategoryFilters 
        activeFilter={activeFilter}
        setActiveFilter={setActiveFilter}
        counts={counts}
      />
      
      <RegistrosTable 
        registros={getFilteredRegistros()}
        emptyMessage="Nenhum registro encontrado"
      />
    </div>
  );
};

// Página de Divergências
const DivergenciasPage = ({ data }) => {
  if (!data) {
    return (
      <div className="empty-state" data-testid="divergencias-page-empty">
        <AlertTriangle size={64} className="empty-icon" />
        <h2>Nenhuma análise</h2>
        <p>Faça upload de um PDF para detectar divergências</p>
      </div>
    );
  }

  const totalDivergencias = data.divergencias?.reduce((acc, d) => acc + (d.divergencia || 0), 0) || 0;

  return (
    <div className="page-content" data-testid="divergencias-page">
      <div className="page-header">
        <div>
          <h2 className="flex items-center gap-2">
            <AlertTriangle size={24} className="text-danger" />
            Divergências de Tarifa
          </h2>
          <p>{data.divergencias?.length || 0} divergências encontradas · Diferença total: {formatCurrency(totalDivergencias)}</p>
        </div>
        <div className="date-display" data-testid="divergencias-date">
          <Calendar size={18} />
          {data.data_relatorio}
        </div>
      </div>

      <div className="stats-grid stats-grid-3">
        <div className="stat-card stat-card-danger" data-testid="stat-total-divergencias">
          <span className="stat-card-title">TOTAL DIVERGÊNCIAS</span>
          <div className="stat-card-value">{data.divergencias?.length || 0}</div>
        </div>
        <div className="stat-card" data-testid="stat-diferenca-total">
          <span className="stat-card-title">DIFERENÇA TOTAL</span>
          <div className="stat-card-value">{formatCurrency(totalDivergencias)}</div>
        </div>
        <div className="stat-card" data-testid="stat-registros-analisados">
          <span className="stat-card-title">REGISTROS ANALISADOS</span>
          <div className="stat-card-value">{data.registros?.length || 0}</div>
        </div>
      </div>

      <DivergenciasTable divergencias={data.divergencias || []} />
    </div>
  );
};

// Página de Saídas
const SaidasPage = ({ data }) => {
  if (!data) {
    return (
      <div className="empty-state" data-testid="saidas-page-empty">
        <LogOut size={64} className="empty-icon" />
        <h2>Nenhuma saída</h2>
        <p>Faça upload de um PDF para ver saídas previstas</p>
      </div>
    );
  }

  return (
    <div className="page-content" data-testid="saidas-page">
      <div className="page-header">
        <div>
          <h2>Saídas Previstas</h2>
          <p>{data.saidas?.length || 0} saídas próximas · {data.registros?.length || 0} total no relatório</p>
        </div>
        <div className="date-display" data-testid="saidas-date">
          <Calendar size={18} />
          {data.data_relatorio}
        </div>
      </div>

      <div className="table-container">
        <div className="table-header">
          <h3>Todas as Saídas do Relatório</h3>
          <span>{data.saidas?.length || 0} registros</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>UH</th>
              <th>NOME</th>
              <th>CAT.</th>
              <th>DIÁRIA</th>
              <th>PARTIDA</th>
              <th>CLIENTE</th>
            </tr>
          </thead>
          <tbody>
            {(data.saidas?.length || 0) === 0 ? (
              <tr>
                <td colSpan="6" className="empty-message">
                  Nenhuma saída encontrada
                </td>
              </tr>
            ) : (
              data.saidas.map((reg, idx) => (
                <tr key={idx} data-testid={`saida-row-${idx}`}>
                  <td className="font-mono">{reg.uh}</td>
                  <td className="text-ellipsis">{reg.nome}</td>
                  <td>
                    <span className={`badge badge-${reg.tipo_classificacao?.toLowerCase()}`}>
                      {reg.tipo_classificacao}
                    </span>
                  </td>
                  <td className="font-mono">{formatCurrency(reg.diaria)}</td>
                  <td>{reg.partida}</td>
                  <td className="text-ellipsis">{reg.cliente}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Página de Upload
const UploadPage = ({ onUpload, isLoading }) => {
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUpload(e.dataTransfer.files[0]);
    }
  }, [onUpload]);

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0]);
    }
  };

  return (
    <div className="page-content" data-testid="upload-page">
      <div className="page-header">
        <h2>Upload de Relatório</h2>
        <p>Carregue o PDF do relatório hoteleiro para análise</p>
      </div>

      <div 
        className={`upload-zone ${dragActive ? 'active' : ''} ${isLoading ? 'loading' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        data-testid="upload-zone"
      >
        <input
          type="file"
          accept=".pdf"
          onChange={handleChange}
          className="upload-input"
          id="file-upload"
          disabled={isLoading}
        />
        <label htmlFor="file-upload" className="upload-label">
          {isLoading ? (
            <>
              <RefreshCw size={48} className="animate-spin" />
              <span>Processando PDF...</span>
            </>
          ) : (
            <>
              <Upload size={48} />
              <span>Arraste o PDF aqui ou clique para selecionar</span>
              <small>Apenas arquivos .pdf são aceitos</small>
            </>
          )}
        </label>
      </div>

      <div className="upload-info">
        <h3>O que será analisado pelo Nexus AI:</h3>
        <ul>
          <li><ChevronRight size={16} /> Extração neural de itens e quantidades via GPT-4o Vision</li>
          <li><ChevronRight size={16} /> Categorização inteligente de fornecedores e produtos</li>
          <li><ChevronRight size={16} /> Identificação de divergências em faturas e boletos</li>
          <li><ChevronRight size={16} /> Auditoria hoteleira completa (hóspedes, saídas, revenue)</li>
          <li><ChevronRight size={16} /> Exportação automatizada para Excel e Auditoria</li>
        </ul>
      </div>
    </div>
  );
};

// Exportar dados
const exportToCSV = (data, filename) => {
  if (!data || !data.registros) return;
  
  const headers = ['UH', 'Nome', 'Categoria', 'Diária', 'Cliente', 'Chegada', 'Partida', 'Observação'];
  const rows = data.registros.map(r => [
    r.uh, r.nome, r.tipo_classificacao, r.diaria, r.cliente, r.chegada, r.partida, r.observacao
  ]);
  
  const csvContent = [headers, ...rows]
    .map(row => row.map(cell => `"${String(cell || '').replace(/"/g, '""')}"`).join(','))
    .join('\n');
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
};

function App() {
  const [activeTab, setActiveTab] = useState('upload');
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [extractionStatus, setExtractionStatus] = useState('');
  const [error, setError] = useState(null);

  const handleUpload = async (file) => {
    setIsLoading(true);
    setExtractionStatus('Iniciando processamento neural...');
    setError(null);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      setTimeout(() => setExtractionStatus('Mapeando campos via GPT-4o Vision...'), 2000);
      setTimeout(() => setExtractionStatus('Auditando divergências de tarifa...'), 4000);
      
      const response = await axios.post(`${API}/upload-pdf`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setData(response.data);
      setExtractionStatus('Extração concluída com sucesso!');
      setTimeout(() => setActiveTab('dashboard'), 800);
    } catch (err) {
      console.error('Erro no upload:', err);
      setError(err.response?.data?.detail || 'Erro ao processar PDF. Verifique se o Backend na Railway está online.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setData(null);
    setActiveTab('upload');
  };

  const handlePrint = () => {
    window.print();
  };

  const handleExport = () => {
    if (data) {
      exportToCSV(data, `nexus_auditoria_${data.data_relatorio?.replace(/\//g, '-')}.csv`);
    }
  };

  const renderContent = () => {
    switch(activeTab) {
      case 'dashboard':
        return <Dashboard data={data} onClear={handleClear} onPrint={handlePrint} />;
      case 'registros':
        return <RegistrosPage data={data} />;
      case 'divergencias':
        return <DivergenciasPage data={data} />;
      case 'saidas':
        return <SaidasPage data={data} />;
      case 'upload':
      default:
        return (
          <>
            {isLoading && (
              <div className="neural-loading-overlay">
                <div className="neural-core">
                  <div className="neural-ring"></div>
                  <Cpu size={48} className="neural-icon animate-pulse" />
                </div>
                <p className="neural-status">{extractionStatus}</p>
              </div>
            )}
            <UploadPage onUpload={handleUpload} isLoading={isLoading} />
          </>
        );
    }
  };

  return (
    <div className="app-container" data-testid="app-container">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="main-content">
        <div className="breaking-news-ticker">
          <Zap size={14} />
          <span>{BREAKING_NEWS}</span>
        </div>

        {error && (
          <div className="error-banner" data-testid="error-banner">
            <AlertTriangle size={20} />
            <span>{error}</span>
            <button onClick={() => setError(null)}>
              <X size={18} />
            </button>
          </div>
        )}
        
        {renderContent()}
        
        {data && (
          <button 
            className="export-fab" 
            onClick={handleExport}
            data-testid="btn-export"
            title="Exportar CSV"
          >
            <Download size={24} />
          </button>
        )}
      </main>
    </div>
  );
}

export default App;
