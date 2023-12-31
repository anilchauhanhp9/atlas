import pandas as pd
import numpy as np
import warnings

TAXONMIC_LEVELS = ["kindom", "phylum", "class", "order", "family", "genus", "species"]


def tax2table(Taxonomy_Series, split_character=";", remove_prefix=False):
    """
    Transforms (green_genes) taxonomy to a table
    Expect the following input format:
    d__Bacteria;p__Bacteroidota;c__Bacteroidia;f__

    Replaces empty values and can remove prefix 'c__'

    """

    if Taxonomy_Series.isnull().any():
        warnings.warn(
            "Some samples have no taxonomy asigned based on checkm. Samples:\n"
            + ", ".join(Taxonomy_Series.index[Taxonomy_Series.isnull()])
        )
        Taxonomy_Series = Taxonomy_Series.dropna().astype(str)

    Tax = pd.DataFrame(
        list(Taxonomy_Series.apply(lambda s: s.split(split_character))),
        index=Taxonomy_Series.index,
    )

    Tax.columns = TAXONMIC_LEVELS[: len(Tax.columns)]

    if remove_prefix:
        Tax = Tax.applymap(lambda s: s[3:]).replace("", np.nan)
    else:
        Tax[Tax.applymap(len) == 3] = np.nan

    return Tax


def clr(data, log=np.log2):
    "Convert counts data to centered log ratio with log2. "
    "Zeros are replaced by multiplicative_replacement from scikit-bio. "
    "See wikipedia for centered log ratio."

    from skbio.stats import composition

    # remove columns with all zeros
    data = data.loc[:, ~(data == 0).all()]

    # dataframe with replaced zeros
    data = pd.DataFrame(
        composition.multiplicative_replacement(data),
        columns=data.columns,
        index=data.index,
    )

    data = log(data)
    data = (data.T - data.mean(1)).T

    return data


def get_kegg_names(json_file):
    "get kegg names "
    "input files can be downloaded from https://www.genome.jp/kegg-bin/get_htext?ko00001"

    import json

    json_tree = json.load(open(json_file))

    Names = {}

    def parse_kegg_json(json_tree):

        # print(json_tree['name'])

        if "children" in json_tree:
            for child in json_tree["children"]:
                parse_kegg_json(child)
        else:
            # last level

            id, Description = json_tree["name"].split(maxsplit=1)

            Names[id] = Description.split(" [")[0]

    parse_kegg_json(json_tree)

    Names = pd.Series(Names, name="Name")

    return Names


def correct_pvalues_for_multiple_testing(pvalues, correction_type="Benjamini-Hochberg"):
    """
    correction_type: one of "Bonferroni", "Bonferroni-Holm", "Benjamini-Hochberg"
    consistent with R - print correct_pvalues_for_multiple_testing([0.0, 0.01, 0.029, 0.03, 0.031, 0.05, 0.069, 0.07, 0.071, 0.09, 0.1])
    """
    from numpy import array, empty

    pvalues = array(pvalues)

    # sort p vlaues and prepare unsort index
    sort_index = np.argsort(pvalues)
    pvalues = pvalues[sort_index]
    unsort_index = np.argsort(sort_index)

    n = pvalues.shape[0]
    new_pvalues = empty(n)
    n = float(n)

    if correction_type == "Bonferroni":
        new_pvalues = n * pvalues
    elif correction_type == "Bonferroni-Holm":
        values = [(pvalue, i) for i, pvalue in enumerate(pvalues)]
        values.sort()
        for rank, vals in enumerate(values):
            pvalue, i = vals
            new_pvalues[i] = (n - rank) * pvalue
    elif correction_type == "Benjamini-Hochberg":
        values = [(pvalue, i) for i, pvalue in enumerate(pvalues)]
        values.sort()
        values.reverse()
        new_values = []
        for i, vals in enumerate(values):
            rank = n - i
            pvalue, index = vals
            new_values.append((n / rank) * pvalue)
        for i in range(0, int(n) - 1):
            if new_values[i] < new_values[i + 1]:
                new_values[i + 1] = new_values[i]
        for i, vals in enumerate(values):
            pvalue, index = vals
            new_pvalues[index] = new_values[i]

    return new_pvalues[unsort_index]
