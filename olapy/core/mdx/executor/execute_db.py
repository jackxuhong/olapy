"""
Part of :mod:`execute.py` module, here olapy construct cube from DATABASE
automatically based on
`start schema model <http://datawarehouse4u.info/Data-warehouse-schema-architecture-star-schema.html>`_
"""

from __future__ import absolute_import, division, print_function, \
    unicode_literals

from collections import Iterable

import pandas as pd
import pandas.io.sql as psql
from sqlalchemy import inspect

from olapy.core.mdx.tools.connection import get_dialect_name_from_conn_string


def load_tables_db(executor):
    """
    Load tables from database.

    :param executor: MdxEngine instance
    :return: tables dict with table name as key and dataframe as value
    """

    tables = {}
    print('Connection string = ' + str(executor.sqla_engine))
    inspector = inspect(executor.sqla_engine)
    # fix all postgres table  names are lowercase
    # load_tables is executed before construct_star_schema
    dialect_name = get_dialect_name_from_conn_string(str(executor.sqla_engine))
    if 'postgres' in dialect_name:
        executor.facts = executor.facts.lower()
    for table_name in inspector.get_table_names():
        if 'oracle' in dialect_name and table_name.upper() == 'FACTS':
            table_name = table_name.title()

        results = executor.sqla_engine.execution_options(
            stream_results=True,
        ).execute('SELECT * FROM {}'.format(table_name),)
        # Fetch all the results of the query
        value = pd.DataFrame(
            iter(results),
            columns=results.keys(),
        )  # Pass results as an iterator
        # with string_folding_wrapper we loose response time
        # value = pd.DataFrame(string_folding_wrapper(results),columns=results.keys())
        tables[table_name] = value[[
            col for col in value.columns if col.lower()[-3:] != '_id'
        ]]

    return tables


def construct_star_schema_db(executor):
    """
    Construct star schema DataFrame from database.

    :param executor: MdxEngine instance
    :return: star schema DataFrame
    """

    fusion = psql.read_sql_query(
        'SELECT * FROM {}'.format(executor.facts,),
        executor.sqla_engine,
    )
    inspector = inspect(executor.sqla_engine)

    for db_table_name in inspector.get_table_names():
        try:
            db_table_name = str(db_table_name)
        except Exception:
            if isinstance(db_table_name, Iterable):
                db_table_name = db_table_name[0]
        try:
            fusion = fusion.merge(
                psql.read_sql_query(
                    "SELECT * FROM {}".format(db_table_name),
                    executor.sqla_engine,
                ),)
        except BaseException:
            print('No common column between {} and {}'.format(
                executor.facts,
                db_table_name,
            ))
            pass

    return fusion
