from sqlalchemy.orm.properties import ColumnProperty

class UpperComparator(ColumnProperty.Comparator):
    """Upper case strings to compare them without regard to case."""
    def __eq__(self, other):
        return func.upper(self.__clause_element__()) == func.upper(other)
