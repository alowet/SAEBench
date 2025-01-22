import os
import matplotlib.pyplot as plt
from tqdm import tqdm
import numpy as np

import sae_bench.sae_bench_utils.general_utils as general_utils
import sae_bench.sae_bench_utils.graphing_utils as graphing_utils

model_name = "gemma-2-2b"
layer = 12

sae_regex_patterns_65k = [
    r"saebench_gemma-2-2b_width-2pow16_date-0108(?!.*step).*",
    r"65k_temp1000.*",  # matryoshka 65k
]

sae_regex_patterns_16k = [
    r"saebench_gemma-2-2b_width-2pow14_date-0108(?!.*step).*",
    r".*notemp.*",  # matryoshka 16k
]
selection_title = "SAE Bench Gemma-2-2B Width Diff Series"

results_folders = ["./graphing_eval_results_0119", "./matroyshka_eval_results_0117"]

baseline_folder = results_folders[0]

eval_types = [
    # "core",
    # "autointerp",
    # "absorption",
    "scr",
    "tpp",
    # "unlearning",
    "sparse_probing",
]

title_prefix = f"{selection_title} Layer {layer}\n"

ks_lookup = {
    "scr": [5, 10, 20, 50, 100, 500],
    "tpp": [5, 10, 20, 50, 100, 500],
    "sparse_probing": [1, 2, 5],
}

baseline_type = "pca_sae"
include_baseline = False


def convert_to_1_minus_score(eval_results, custom_metric, baseline_value=None):
    for sae_name in eval_results:
        score = eval_results[sae_name][custom_metric]
        eval_results[sae_name][custom_metric] = 1 - score
    if baseline_value:
        baseline_value = 1 - baseline_value
    return eval_results, baseline_value


def get_mean_metric_over_k(eval_results, eval_type, ks):
    """Calculate mean metric value over all k values for a given eval type."""
    mean_results = {}

    for sae_name in eval_results:
        mean_results[sae_name] = eval_results[sae_name].copy()
        k_dependent_values = []
        for k in ks:
            metric_key, _ = graphing_utils.get_custom_metric_key_and_name(eval_type, k)
            if metric_key in eval_results[sae_name]:
                k_dependent_values.append(eval_results[sae_name][metric_key])

        if k_dependent_values:
            mean_metric_key, _ = graphing_utils.get_custom_metric_key_and_name(eval_type, "mean")
            mean_results[sae_name][mean_metric_key] = np.mean(k_dependent_values)

    return mean_results


def get_max_metric_over_k(eval_results, eval_type, ks):
    """Calculate max metric value over all k values for a given eval type."""
    max_results = {}

    for sae_name in eval_results:
        max_results[sae_name] = eval_results[sae_name].copy()
        k_dependent_values = []
        for k in ks:
            metric_key, _ = graphing_utils.get_custom_metric_key_and_name(eval_type, k)
            if metric_key in eval_results[sae_name]:
                k_dependent_values.append(eval_results[sae_name][metric_key])

        if k_dependent_values:
            max_metric_key, _ = graphing_utils.get_custom_metric_key_and_name(eval_type, "max")
            max_results[sae_name][max_metric_key] = np.max(k_dependent_values)

    return max_results


# Create images directory
image_path = "./images_paper_mean"
if not os.path.exists(image_path):
    os.makedirs(image_path)

# Process each eval type separately
for eval_type in tqdm(eval_types):
    # Load data
    eval_folders = []
    core_folders = []

    for results_folder in results_folders:
        eval_folders.append(f"{results_folder}/{eval_type}")
        core_folders.append(f"{results_folder}/core")

    eval_filenames = graphing_utils.find_eval_results_files(eval_folders)
    core_filenames = graphing_utils.find_eval_results_files(core_folders)

    filtered_eval_filenames_65k = general_utils.filter_with_regex(
        eval_filenames, sae_regex_patterns_65k
    )
    filtered_core_filenames_65k = general_utils.filter_with_regex(
        core_filenames, sae_regex_patterns_65k
    )
    filtered_eval_filenames_16k = general_utils.filter_with_regex(
        eval_filenames, sae_regex_patterns_16k
    )
    filtered_core_filenames_16k = general_utils.filter_with_regex(
        core_filenames, sae_regex_patterns_16k
    )

    eval_results_65k = graphing_utils.get_eval_results(filtered_eval_filenames_65k)
    core_results_65k = graphing_utils.get_core_results(filtered_core_filenames_65k)
    eval_results_16k = graphing_utils.get_eval_results(filtered_eval_filenames_16k)
    core_results_16k = graphing_utils.get_core_results(filtered_core_filenames_16k)

    # Add core results to eval results
    for sae in eval_results_65k:
        eval_results_65k[sae].update(core_results_65k[sae])
    for sae in eval_results_16k:
        eval_results_16k[sae].update(core_results_16k[sae])

    # Get k values for this eval type if it uses k
    ks = ks_lookup.get(eval_type, [-1])

    if ks != [-1]:  # If this eval type uses k values
        # Calculate mean and max over all k values
        eval_results_65k_mean = get_mean_metric_over_k(eval_results_65k, eval_type, ks)
        eval_results_16k_mean = get_mean_metric_over_k(eval_results_16k, eval_type, ks)
        eval_results_65k_max = get_max_metric_over_k(eval_results_65k, eval_type, ks)
        eval_results_16k_max = get_max_metric_over_k(eval_results_16k, eval_type, ks)

        # Create plots for both mean and max
        for metric_type in ["mean", "max"]:
            if metric_type == "mean":
                eval_results_65k_current = eval_results_65k_mean
                eval_results_16k_current = eval_results_16k_mean
            else:
                eval_results_65k_current = eval_results_65k_max
                eval_results_16k_current = eval_results_16k_max

            custom_metric, custom_metric_name = graphing_utils.get_custom_metric_key_and_name(
                eval_type, metric_type
            )

            if include_baseline:
                if model_name != "gemma-2-9b":
                    baseline_sae_path = (
                        f"{model_name}_layer_{layer}_pca_sae_custom_sae_eval_results.json"
                    )
                    baseline_sae_path = os.path.join(baseline_folder, eval_type, baseline_sae_path)
                    baseline_label = "PCA Baseline"
            else:
                baseline_sae_path = None
                baseline_label = None

            if baseline_sae_path:
                baseline_results = graphing_utils.get_eval_results([baseline_sae_path])
                baseline_filename = os.path.basename(baseline_sae_path)
                baseline_results_key = baseline_filename.replace("_eval_results.json", "")
                core_baseline_filename = baseline_sae_path.replace(eval_type, "core")

                baseline_results[baseline_results_key].update(
                    graphing_utils.get_core_results([core_baseline_filename])[baseline_results_key]
                )
                if metric_type == "mean":
                    baseline_results = get_mean_metric_over_k(baseline_results, eval_type, ks)
                else:
                    baseline_results = get_max_metric_over_k(baseline_results, eval_type, ks)
                baseline_value = baseline_results[baseline_results_key][custom_metric]
            else:
                baseline_value = None

            # Convert absorption scores if needed
            if custom_metric == "mean_absorption_fraction_score":
                eval_results_65k_current, baseline_value = convert_to_1_minus_score(
                    eval_results_65k_current, custom_metric, baseline_value
                )
                eval_results_16k_current, baseline_value = convert_to_1_minus_score(
                    eval_results_16k_current, custom_metric, baseline_value
                )

            # Map 65k to 16k keys
            map_65k_to_16k = lambda sae_key: sae_key.replace(
                "width-2pow16", "width-2pow14"
            ).replace(
                "matryoshka_gemma-2-2b-16k-v2_MatryoshkaBatchTopKTrainer_65k_temp1000_google_gemma-2-2b_ctx1024_0117_resid_post_layer_12",
                "matryoshka_gemma-2-2b-16k-v2_MatryoshkaBatchTopKTrainer_notemp_google_gemma-2-2b_ctx1024_0114_resid_post_layer_12",
            )

            # Calculate differences
            eval_results_diff = {}
            for sae_key_65k in eval_results_65k_current:
                eval_results_diff[sae_key_65k] = {}
                for metric_key in eval_results_65k_current[sae_key_65k]:
                    if metric_key == custom_metric:
                        sae_key_16k = map_65k_to_16k(sae_key_65k)
                        eval_results_diff[sae_key_65k][metric_key] = (
                            eval_results_65k_current[sae_key_65k][metric_key]
                            - eval_results_16k_current[sae_key_16k][metric_key]
                        )
                    else:
                        eval_results_diff[sae_key_65k][metric_key] = eval_results_65k_current[
                            sae_key_65k
                        ][metric_key]

            # Create plot
            plt.figure(figsize=(10, 6))
            ax = plt.gca()

            # title = f"{title_prefix}L0 vs {custom_metric_name}"
            # title += f" ({metric_type.capitalize()} over k={min(ks)}-{max(ks)})"
            title = ""

            graphing_utils.plot_2var_graph(
                eval_results_diff,
                custom_metric,
                y_label=custom_metric_name,
                title=title,
                baseline_value=baseline_value,
                baseline_label=baseline_label,
                passed_ax=ax,
                legend_mode="show_outside",
                connect_points=True,
                bold_x0=True,
            )

            # Save plot
            image_name = f"plot_diff_{selection_title.replace(' ', '_').lower()}_{eval_type}_layer_{layer}_{metric_type}.png"
            plt.tight_layout()
            plt.savefig(os.path.join(image_path, image_name))
            plt.close()

    else:
        # Handle non-k-dependent eval types as before
        custom_metric, custom_metric_name = graphing_utils.get_custom_metric_key_and_name(
            eval_type, -1
        )

        # [Rest of the original code for non-k-dependent eval types...]
        # (Previous code for baseline, absorption scores, differences, and plotting)
        if include_baseline:
            if model_name != "gemma-2-9b":
                baseline_sae_path = (
                    f"{model_name}_layer_{layer}_pca_sae_custom_sae_eval_results.json"
                )
                baseline_sae_path = os.path.join(baseline_folder, eval_type, baseline_sae_path)
                baseline_label = "PCA Baseline"
        else:
            baseline_sae_path = None
            baseline_label = None

        if baseline_sae_path:
            baseline_results = graphing_utils.get_eval_results([baseline_sae_path])
            baseline_filename = os.path.basename(baseline_sae_path)
            baseline_results_key = baseline_filename.replace("_eval_results.json", "")
            core_baseline_filename = baseline_sae_path.replace(eval_type, "core")

            baseline_results[baseline_results_key].update(
                graphing_utils.get_core_results([core_baseline_filename])[baseline_results_key]
            )
            baseline_value = baseline_results[baseline_results_key][custom_metric]
        else:
            baseline_value = None

        # Convert absorption scores if needed
        if custom_metric == "mean_absorption_fraction_score":
            eval_results_65k, baseline_value = convert_to_1_minus_score(
                eval_results_65k, custom_metric, baseline_value
            )
            eval_results_16k, baseline_value = convert_to_1_minus_score(
                eval_results_16k, custom_metric, baseline_value
            )

        # Map 65k to 16k keys and calculate differences
        map_65k_to_16k = lambda sae_key: sae_key.replace("width-2pow16", "width-2pow14").replace(
            "matryoshka_gemma-2-2b-16k-v2_MatryoshkaBatchTopKTrainer_65k_temp1000_google_gemma-2-2b_ctx1024_0117_resid_post_layer_12",
            "matryoshka_gemma-2-2b-16k-v2_MatryoshkaBatchTopKTrainer_notemp_google_gemma-2-2b_ctx1024_0114_resid_post_layer_12",
        )

        # Calculate differences
        eval_results_diff = {}
        for sae_key_65k in eval_results_65k:
            eval_results_diff[sae_key_65k] = {}
            for metric_key in eval_results_65k[sae_key_65k]:
                if metric_key == custom_metric:
                    sae_key_16k = map_65k_to_16k(sae_key_65k)
                    eval_results_diff[sae_key_65k][metric_key] = (
                        eval_results_65k[sae_key_65k][metric_key]
                        - eval_results_16k[sae_key_16k][metric_key]
                    )
                else:
                    eval_results_diff[sae_key_65k][metric_key] = eval_results_65k[sae_key_65k][
                        metric_key
                    ]

        # Create plot
        plt.figure(figsize=(10, 6))
        ax = plt.gca()

        title = f""

        graphing_utils.plot_2var_graph(
            eval_results_diff,
            custom_metric,
            y_label=custom_metric_name,
            title=title,
            baseline_value=baseline_value,
            baseline_label=baseline_label,
            passed_ax=ax,
            legend_mode="show_outside",
            connect_points=True,
            bold_x0=True,
        )

        # Save plot
        image_name = (
            f"plot_diff_{selection_title.replace(' ', '_').lower()}_{eval_type}_layer_{layer}.png"
        )
        plt.tight_layout()
        plt.savefig(os.path.join(image_path, image_name))
        plt.close()
