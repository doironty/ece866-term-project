clear all; close all; clc; %#ok<CLALL>
addpath(fullfile(pwd,'..','src','time_frequency'));

ANALYSIS_ON       = true;
TIMING_METRICS_ON = true;

% --- Data ---
DATE_FILE_1 = fullfile(pwd,'..','doc','deliverables','data','site1_evi.mat');
DATE_FILE_2 = fullfile(pwd,'..','doc','deliverables','data','site2_evi.mat');
DATE_FILE_3 = fullfile(pwd,'..','doc','deliverables','data','site3_evi.mat');

% --- Analysis ---
if ANALYSIS_ON
    % --- DWT ---
    analyzeDWT(DATE_FILE_1);
    analyzeDWT(DATE_FILE_2);
    analyzeDWT(DATE_FILE_3);
    
    % --- CWT ---
    analyzeCWT(DATE_FILE_1);
    analyzeCWT(DATE_FILE_2);
    analyzeCWT(DATE_FILE_3);
    
    % --- EMD ---
    analyzeEMD(DATE_FILE_1);
    analyzeEMD(DATE_FILE_2);
    analyzeEMD(DATE_FILE_3);
end

% --- Timing Metrics ---
if TIMING_METRICS_ON
    tm = TimingMetrics();

    tm.loadData(DATE_FILE_1);
    tm.extractMetrics();

    tm.loadData(DATE_FILE_2);
    tm.extractMetrics();

    tm.loadData(DATE_FILE_3);
    tm.extractMetrics();
end
