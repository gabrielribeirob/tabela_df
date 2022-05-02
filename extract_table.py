from py_pdf_parser.loaders import load_file
from py_pdf_parser.visualise import visualise
import tabula, re

class ExtractTabel:
  def __init__(self, path):
    self.path = path
    self.FONT_MAPPING = {      
      'Arial,Bold,11.0': 'titulo',
      'Arial,9.1': 'subtitulo',
      'Arial,Bold,7.9': 'coluna',
      'Arial,Bold,7.0': 'coluna',
      'Arial,7.9': 'conteudo',
      'Arial,Bold,12.0': 'titulo_tabela',
      'Arial,12.0': 'texto'
      }
    self.document = load_file(self.path, font_mapping=self.FONT_MAPPING)
    self.tables = self.extract_tables()
    self.get_summary_pages = self._get_summary_pages()

  def _get_summary_pages(self):
    """ Extrai as páginas em que as tabelas, os relatórios e as notas explicativas
    estão no pdf a partir do sumário do mesmo


    Returns:
        Dict: Contém como chave o nome do item e como valor o número da página
    """
    summary                      = self.document.get_page(1)
    df_individual_element        = (
        summary.elements.filter_by_font("titulo")
        .filter_by_text_equal("DFs Individuais")
        .extract_single_element()
    )
    pareceres_declaracoes_element = (
        summary.elements.filter_by_font("titulo")
        .filter_by_text_equal("Pareceres e Declarações")
        .extract_single_element()
    )
    order_summary_section = self.document.sectioning.create_section(
        name="dfs",
        start_element=df_individual_element,
        end_element=pareceres_declaracoes_element,
        include_last_element=False
    )
    d           = {}
    page        = []
    tables_name = []
    for i in order_summary_section.elements.filter_by_font('subtitulo'):
      pages      = re.match(r'\d+', i.text())
      table_name = re.match(r'[A-Za-z]+.+', i.text())
      if pages != None:
        page.append(int(pages.group()))
      else:
        tables_name.append(table_name.group())

    for i in range(len(page)):
      d[tables_name[i]] = page[i]

    return d
  
  def get_summary_tables_pages(self):
    """ Extrai apenas as páginas que contém tabelas no pdf

    Returns:
        List: Uma lista com o número das páginas referentes à tabelas (DFs e DMP) do pdf
    """
    d = self._get_summary_pages()
    keys = [k for k,v in d.items() if re.match(r'Relat.+|Nota.+', k) == None]
    d_filter = [{v: d[v]} for i,v in enumerate(keys)]
    return [list(i.values())[0]+1 for i in d_filter]

  def _get_dmpl_columns_names(self, page):
    """ Separa as tabelas de "Demonstração das Mutações do Patrimônio Líquido"
        e corrige o nome das colunas colocandos-as na ordem correta

    Args:
        page (int): número da página que contém a tabela 

    Returns:
        Lista: Contém strings com os nomes das colunas da tabela DMP seguindo a ordem do pdf
    """
    table1       = self.document.get_page(7)
    order        = [3, 0, 4, 7, 1, 5, 6, 2]
    column_names = [i.text().strip().replace('\n','') for i in table1.elements.filter_by_font('coluna')]
    column_names = [column_names[i] for i in order]
    return column_names 
  
  def _get_dfs_columns_names(self, page):
    """Separa as tabelas de "Demonstração Financeira Individual ou Consolidada" 
        e corrige o nome das colunas colocandos-as na ordem correta
    Args:
        page (int): número da página que contém a tabela 

    Returns:
        List: Contém strings com os nomes das colunas da tabela DF seguindo a ordem do pdf
    """
    table1           = self.document.get_page(page)
    order            = [1, 0, 2, 3, 4]
    column_names     = [i.text().strip().replace('\n','') for i in table1.elements.filter_by_font('coluna')]
    column_names[-2] = str('Penúltimo Exercício ') + column_names[-2]
    column_names[-1] = column_names[-1].replace('Penúltimo Exercício','').strip()
    column_names     = [column_names[i] for i in order]
    return column_names  

  def get_table_name(self, page):
    """ Extrai o nome das tabelas
    Args:
        page (int): número da página que contém a tabela 

    Returns:
        String: Contém o nome da tabela referente à página supracitada
    """
    document = self.document.get_page(page)
    titulo_tabela = (
      document.elements.filter_by_font("titulo_tabela")
      .extract_single_element()
    )
    return titulo_tabela

  def get_tables(self, page):
    """ Realiza a busca completa das tabelas, filtrando-as segundo seu tipo e limpando 
    caso tenha necessidade 
    Args:
        page (int): número da página que contém a tabela 

    Returns:
        List: Contém Dataframes da sessão DMP e DF
    """
    titulo_tabela = self.get_table_name(page)
    if 'DMPL' in titulo_tabela.text():
      table = tabula.read_pdf(self.path,pages=page)
      table = table[0]
      table = table.set_axis(self._get_dmpl_columns_names(page), axis=1)
      table = table.drop([table.index[0], table.index[1]])
    else:
      table = tabula.read_pdf(self.path,pages=page)
      table = table[0]
      table = table.set_axis(self._get_dfs_columns_names(page), axis=1)
      table = table.drop(0)
    return table

  def extract_tables(self):
    """ Realiza a extração completa das tabelas devolvendo uma lista de DataFrames

    Returns:
        Dict: Contém um dicionário com o nome da tabela como chave e o DataFrame correspondente
    """
    pages = self.get_summary_tables_pages()
    d = {}
    for i in pages:
      try:
       d[self.get_table_name(i).text()] = self.get_tables(i)
       
      except:
        pass
    return d


e = ExtractTabel('5870_020052_20042022112429-converted.pdf')
print(e.tables)

