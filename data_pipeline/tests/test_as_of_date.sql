select
    to_date('{{ var("as_of_date") }}') as as_of_date

where
    to_date('{{ var("as_of_date") }}')
    != last_day(to_date('{{ var("as_of_date") }}'))
