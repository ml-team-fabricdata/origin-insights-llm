from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from table_constants import DatabaseSchema, TableInfo

class BaseQuery(ABC):
    """Clase base abstracta para todas las queries.
    Define la interfaz común que deben implementar todas las queries.
    """
    
    def __init__(self):
        self.params: List[Any] = []
    
    @abstractmethod
    def build_query(self) -> str:
        """
        Construye y retorna la query SQL.
        Debe ser implementado por las clases hijas.
        """
        pass
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Prepara la query y sus parámetros para ejecución.
        Retorna un diccionario con la query y sus parámetros.
        
        Returns:
            Dict con:
                - query: str - La query SQL
                - params: List - Lista de parámetros
        """
        pass
        self.schema = DatabaseSchema()
    
    @abstractmethod
    def build(self) -> str:
        """Construye la query SQL"""
        pass
    
    def get_params(self) -> List[Any]:
        """Retorna los parámetros de la query"""
        return self.params
    
    def execute(self) -> Dict[str, Any]:
        """Retorna la query y sus parámetros"""
        return {
            "query": self.build(),
            "params": self.get_params()
        }

class BaseSearchQuery(BaseQuery):
    """Clase base para queries de búsqueda"""
    
    def __init__(
        self,
        table: TableInfo,
        search_columns: List[str],
        return_columns: Optional[List[str]] = None,
        use_fuzzy: bool = False
    ):
        super().__init__()
        self.table = table
        self.search_columns = search_columns
        self.return_columns = return_columns or ['*']
        self.use_fuzzy = use_fuzzy
    
    def build(self) -> str:
        return f"""
        SELECT {', '.join(self.return_columns)}
        FROM {self.table.full_name}
        WHERE {self._build_where_clause()}
        {self._build_order_clause()}
        """
    
    def _build_where_clause(self) -> str:
        raise NotImplementedError
    
    def _build_order_clause(self) -> str:
        return ""

class BaseJoinQuery(BaseQuery):
    """Clase base para queries con joins"""
    
    def __init__(
        self,
        main_table: TableInfo,
        joins: Dict[TableInfo, str]
    ):
        super().__init__()
        self.main_table = main_table
        self.joins = joins
    
    def build(self) -> str:
        return f"""
        SELECT {self._build_select_clause()}
        FROM {self.main_table.full_name}
        {self._build_joins()}
        {self._build_where_clause()}
        {self._build_group_clause()}
        {self._build_order_clause()}
        """
    
    def _build_select_clause(self) -> str:
        return "*"
    
    def _build_joins(self) -> str:
        join_clauses = []
        for table, condition in self.joins.items():
            join_clauses.append(f"LEFT JOIN {table.full_name} ON {condition}")
        return "\n".join(join_clauses)
    
    def _build_where_clause(self) -> str:
        return ""
    
    def _build_group_clause(self) -> str:
        return ""
    
    def _build_order_clause(self) -> str:
        return ""