select
    dateadd(year, seq4(), '2015-12-31') as valuation_date
from table(generator(rowcount => 15))
