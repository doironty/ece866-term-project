classdef TimingMetrics < matlab.mixin.SetGet
    properties (Constant)
        DEF_PHENO_YEAR_START = 320
        DEF_PHENO_THRESHOLDS = [0.20,0.50,0.80]
        DEF_DWT_WAVELET_NAME = 'dmey'
        DEF_DWT_DECOMPOSITION_LEVEL = 5
        DEF_CWT_WAVELET_NAME = 'amor'
        DEF_CWT_VOICES_PER_OCTAVE = 32
        DEF_EMD_NOISE_STD = 0.2
        DEF_EMD_NUM_ENSEMBLES = 200
        DEF_FIGURE_FONT_NAME = 'CMU Sans Serif'
    end

    properties
    end

    properties (SetAccess = private)
        Config = struct()
        Data = struct()
        Metadata = struct()
        Analysis = struct('DWT',[],'CWT',[],'EMD',[])
        Metrics = struct()
        Stats = []
    end

    properties (Access = private)
        SavePath = []
    end

    methods
        function obj = TimingMetrics(varargin)
            obj.setConfig(varargin{:});
        end

        function loadData(obj,dataFile)
            clc;
            includePackage('math','graphics');
        
            [filepath,name] = fileparts(dataFile);
            savepath = fullfile(filepath,name,'timing_metrics');
            if ~isfolder(savepath)
                mkdir(savepath);
            end
            obj.SavePath = savepath;
            
            obj.loadDataHelper(dataFile);
        end

        function setConfig(obj,varargin)
            obj.setConfigHelper(varargin{:});
        end

        function extractMetrics(obj)
            obj.doDWT();
            obj.doCWT();
            obj.doEMD();
            
            obj.extractMetricsHelper();

            obj.makeStats();
            if obj.Config.Plot
                obj.makePlots();
            end
            obj.saveMetrics();
        end

        function saveMetrics(obj)
            saveStuct.Metrics = obj.Metrics;
            save(fullfile(obj.SavePath,'results.mat'),'-struct','saveStuct');
        end
    end

    methods (Access = private)
        function loadDataHelper(obj,dataFile)
            S = load(dataFile);

            t = double(S.t);
            x = S.x;
            L = double(S.L);
            Ts = double(S.Ts);
        
            tDate = datetime(1970,1,1) + days(t);
            tYears = year(tDate) + (day(tDate,'dayofyear') - 1) ./ 365;
        
            years = unique(year(tDate));
            numYears  = length(years);

            obj.Data.Signal = x;
            obj.Data.Time.Day = t;
            obj.Data.Time.Date = tDate;
            obj.Data.Time.Year = tYears;
            obj.Data.NumSamples = L;
            obj.Data.SamplingPeriod = Ts;

            obj.Metadata.NumYears = numYears;
            obj.Metadata.Years = years;

            obj.Metrics = repmat(...
                struct(...
                    'Method1',[],...
                    'Method2',[],...
                    'Method3',[],...
                    'Method4',[]),...
                numYears,1);
        end

        function setConfigHelper(obj,varargin)
            p = inputParser;
            
            addOptional(p,'Plot',true);
            addOptional(p,'PhenoYearStart',obj.DEF_PHENO_YEAR_START);
            addOptional(p,'PhenoThresholds',obj.DEF_PHENO_THRESHOLDS);
            addOptional(p,'DWTWaveletName',obj.DEF_DWT_WAVELET_NAME);
            addOptional(p,'DWTDecompositionLevel',obj.DEF_DWT_DECOMPOSITION_LEVEL);
            addOptional(p,'CWTWaveletName',obj.DEF_CWT_WAVELET_NAME);
            addOptional(p,'CWTVoicesPerOctave',obj.DEF_CWT_VOICES_PER_OCTAVE);
            addOptional(p,'EMDNoiseStd',obj.DEF_EMD_NOISE_STD);
            addOptional(p,'EMDNumEnsembles',obj.DEF_EMD_NUM_ENSEMBLES);

            parse(p,varargin{:});

            obj.Config.Plot = p.Results.Plot;
            obj.Config.PhenoYearStart = p.Results.PhenoYearStart;
            obj.Config.PhenoThresholds = p.Results.PhenoThresholds;
            obj.Config.DWT.WaveletName = p.Results.DWTWaveletName;
            obj.Config.DWT.DecompositionLevel = p.Results.DWTDecompositionLevel;
            obj.Config.CWT.WaveletName = p.Results.CWTWaveletName;
            obj.Config.CWT.VoicesPerOctave = p.Results.CWTVoicesPerOctave;
            obj.Config.EMD.NoiseStd = p.Results.EMDNoiseStd;
            obj.Config.EMD.NumEnsembles = p.Results.EMDNumEnsembles;
        end

        function extractMetricsHelper(obj)
            tDates = obj.Data.Time.Date;
            numYears = obj.Metadata.NumYears;
            years = obj.Metadata.Years;
            phenoYearStart = obj.Config.PhenoYearStart;
            for ii = 1:numYears
                startDate = datetime(years(ii) - 1,1,1) + days(phenoYearStart - 1);
                endDate = datetime(years(ii),1,1) + days(phenoYearStart - 2);

                inWindow  = tDates >= startDate & tDates < endDate;
                window = find(inWindow);

                for method = 1:4
                    metrics = obj.calcMetrics(years(ii),window,method);
                    obj.Metrics(ii).(sprintf('Method%d',method)) = metrics;
                end  
            end
        end

        function doDWT(obj)
            x = obj.Data.Signal;
            wname = obj.Config.DWT.WaveletName;
            n = obj.Config.DWT.DecompositionLevel;
            N = floor(log2(obj.Data.NumSamples));

            [c,l] = wavedec(x,N,wname);
            annualSignal = wrcoef('d',c,l,wname,n);

            obj.Analysis.DWT.Coefficients = c;
            obj.Analysis.DWT.Bookkeeping = l;
            obj.Analysis.DWT.AnnualSignal = annualSignal;
        end

        function doCWT(obj)
            x = obj.Data.Signal;
            Ts = obj.Data.SamplingPeriod;

            wname = obj.Config.CWT.WaveletName;
            numVoices = obj.Config.CWT.VoicesPerOctave;

            [wt,f,coi] = cwt(x,wname,1 / Ts,'VoicesPerOctave',numVoices);
            period = 1 ./ f;
            
            [~,annualInd] = min(abs(period - 365));
            annualSignal = wt(annualInd,:);
        
            inBand = period >= 365 * 0.8 & period <= 365 * 1.2;
            bandPower = sum(abs(wt(inBand,:)).^2,1);
            
            phase = angle(wt(annualInd,:));
            phaseUnwrapped = unwrap(phase);
            [~,argMax] = max(real(annualSignal));
            refPhase = phaseUnwrapped(argMax);
            
            obj.Analysis.CWT.WaveletTransform = wt;
            obj.Analysis.CWT.Frequency = f;
            obj.Analysis.CWT.Period = period;
            obj.Analysis.CWT.COI.Frequency = coi;
            obj.Analysis.CWT.COI.Period = 1 ./ coi;
            obj.Analysis.CWT.AnnualIndex = annualInd;
            obj.Analysis.CWT.AnnualSignal = annualSignal;
            obj.Analysis.CWT.AnnualBandPower = bandPower;
            obj.Analysis.CWT.AnnualPhase = phase;
            obj.Analysis.CWT.AnnualPhaseUnwrapped = phaseUnwrapped;
            obj.Analysis.CWT.RefPhase = refPhase;
        end

        function doEMD(obj)
            x = obj.Data.Signal;
            L = obj.Data.NumSamples;
            Ts = obj.Data.SamplingPeriod;
            
            noiseStd = obj.Config.EMD.NoiseStd * std(x);
            numEnsembles = obj.Config.EMD.NumEnsembles;
            
            seed = 13;
            rng(seed);
        
            imf0 = emd(x);
            N = size(imf0,2);

            imfSum = zeros(L,N);
            for ii = 1:numEnsembles
                noise = noiseStd * randn(size(x));
                z = x + noise;

                imf = emd(z);
                n = size(imf,2);

                if n < N
                    imf = [imf,zeros(L,N - n)]; %#ok<AGROW>
                elseif n > N
                    imf(:,N) = sum(imf(:,N:end),2);
                    imf = imf(:,1:N);
                end

                imfSum = imfSum + imf;
            end
            imfs = imfSum / numEnsembles;

            meanPeriod = zeros(1,N);
            for ii = 1:N
                hht = hilbert(imfs(:,ii));
                instPhase = unwrap(angle(hht));
                phaseDiff = diff(instPhase);
                instFreq = [phaseDiff(1); phaseDiff] / (2 * pi * Ts);
                validFreq = instFreq(instFreq > 0);
                if ~isempty(validFreq)
                    meanPeriod(ii) = 1 / mean(validFreq);
                end
            end
            
            [~,annualInd] = min(abs(meanPeriod - 365));
            annualSignal = imfs(:,annualInd);
        
            obj.Analysis.EMD.IMF = imfs;
            obj.Analysis.EMD.AnnualIndex = annualInd;
            obj.Analysis.EMD.AnnualSignal = annualSignal;
        end

        function metrics = calcMetrics(obj,year,window,method)
            metrics.NumCycles = nan;
            metrics.Greenup = nan;
            metrics.GreenupMid = nan;
            metrics.Maturity = nan;
            metrics.Peak = nan;
            metrics.Senescence = nan;
            metrics.GreendownMid = nan;
            metrics.Dormancy = nan;
        
            if length(window) < 10
                return;
            end

            thresholds = obj.Config.PhenoThresholds;
            t = obj.Data.Time.Day;
            switch method
                case 1
                    x = obj.Analysis.DWT.AnnualSignal;
                    [minT,maxT] = obj.extractPeakTroughDWT(year,x);
                case 2
                    x = real(obj.Analysis.CWT.AnnualSignal);
                    [minT,maxT] = obj.extractPeakTroughCWT(year,x);
                case 3
                    x = obj.Analysis.CWT.AnnualPhaseUnwrapped;
                    refPhase = obj.Analysis.CWT.RefPhase;
                    maxT = obj.extractPeakCWTPhase(year,x,refPhase);

                    x = real(obj.Analysis.CWT.AnnualSignal);
                    minT = obj.extractPeakTroughCWT(year,x);
                case 4
                    x = obj.Analysis.EMD.AnnualSignal;
                    [minT,maxT] = obj.extractPeakTroughEMD(year,x);
            end
            x = x(window);
            t = t(window);

            [minX,argTrough] = min(x);
            [maxX,argPeak] = max(x);
            ampX = maxX - minX;
            if ampX < 1e-6
                return;
            end
            normX = (x - minX) / ampX;
        
            % Peak/Dormancy
            metrics.Peak = maxT;
            metrics.Dormancy = minT;
        
            % NumCycles
            minProminence = 0.1 * ampX;
            [~,~,~,prominences] = findpeaks(x);

            metrics.NumCycles = nnz(prominences >= minProminence);
        
            % GrennnessOnset/GreenupMid/Maturity
            if argTrough < argPeak
                ascendingInd = argTrough:argPeak;
            else
                ascendingInd = 1:argPeak;
            end

            if length(ascendingInd) >= 3
                xAscending = normX(ascendingInd);
                tAscending = t(ascendingInd);

                metrics.Greenup = obj.thresholdCross(xAscending,tAscending,thresholds(1),'rising');
                metrics.GreenupMid = obj.thresholdCross(xAscending,tAscending,thresholds(2),'rising');
                metrics.Maturity = obj.thresholdCross(xAscending,tAscending,thresholds(3),'rising');
            end
        
            % Senescence/GreendownMid
            if argPeak < argTrough
                descendingInd = argPeak:argTrough;
            else
                descendingInd = argPeak:length(x);
            end

            if length(descendingInd) >= 3
                xDescending = normX(descendingInd);
                tDescending = t(descendingInd);

                metrics.Senescence = obj.thresholdCross(xDescending,tDescending,thresholds(3),'falling');
                metrics.GreendownMid = obj.thresholdCross(xDescending,tDescending,thresholds(2),'falling');
            end
        end

        function [minT,maxT] = extractPeakTroughDWT(obj,year,x)
            tDays = obj.Data.Time.Day;
            tDates = obj.Data.Time.Date;
            phenoYearStart = obj.Config.PhenoYearStart;
            
            minT = nan;
            maxT = nan;

            startDate = datetime(year,1,1) + days(phenoYearStart - 1);
            endDate = datetime(year + 1,1,1) + days(phenoYearStart - 2);
            
            inWindow  = tDates >= startDate & tDates < endDate;
            if sum(inWindow) < 10
                return;
            end

            xWindowed = x(inWindow);
            tWindowed = tDays(inWindow);

            [~,argMin] = min(xWindowed);
            [~,argMax] = max(xWindowed);

            minT = tWindowed(argMin);
            maxT = tWindowed(argMax);
        end

        function [minT,maxT] = extractPeakTroughCWT(obj,year,x)
            tDays = obj.Data.Time.Day;
            tDates = obj.Data.Time.Date;
            phenoYearStart = obj.Config.PhenoYearStart;
            coiPeriod = obj.Analysis.CWT.COI.Period;
            annualIndex = obj.Analysis.CWT.AnnualIndex;
            annualPeriod = obj.Analysis.CWT.Period(annualIndex);
            
            maxT = nan;
            minT = nan;
            
            startDate = datetime(year,1,1) + days(phenoYearStart - 1);
            endDate = datetime(year + 1,1,1) + days(phenoYearStart - 2);

            inWindow = tDates >= startDate & tDates < endDate;
            inCoi = coiPeriod < annualPeriod;
            inWindow = inWindow & ~inCoi(:)';
            if sum(inWindow) < 10
                return;
            end

            xWindowed = x(inWindow);
            tWindowed = tDays(inWindow);

            [~,argMin] = min(xWindowed);
            [~,argMax] = max(xWindowed);

            minT = tWindowed(argMin);
            maxT = tWindowed(argMax);
        end

        function maxT = extractPeakCWTPhase(obj,year,AnnualPhaseUnwrapped,refPhase)
            tDays = obj.Data.Time.Day;
            tDates = obj.Data.Time.Date;
            Ts = obj.Data.SamplingPeriod;
            phenoYearStart = obj.Config.PhenoYearStart;
            coiPeriod = obj.Analysis.CWT.COI.Period;
            annualIndex = obj.Analysis.CWT.AnnualIndex;
            annualPeriod = obj.Analysis.CWT.Period(annualIndex);
            
            maxT = nan;
            
            startDate = datetime(year,1,1) + days(phenoYearStart - 1);
            endDate = datetime(year + 1,1,1) + days(phenoYearStart - 2);

            inWindow = tDates >= startDate & tDates < endDate;
            inCoi = coiPeriod < annualPeriod;
            inWindow = inWindow & ~inCoi(:)';
            if sum(inWindow) < 10
                return;
            end

            phaseWindowed = AnnualPhaseUnwrapped(inWindow);
            tWindowed = tDays(inWindow);
            numCyclesElapsed = floor((phaseWindowed(1) - refPhase) / (2 * pi));
            targetPhase = refPhase + (numCyclesElapsed + 1) * 2 * pi;
            if targetPhase > phaseWindowed(1) && targetPhase <= phaseWindowed(end)
                phaseDiff = phaseWindowed - targetPhase;
                crossings = find(diff(sign(phaseDiff)) > 0);
                if ~isempty(crossings)
                    ind = crossings(1);
                    frac = -phaseDiff(ind) / (phaseDiff(ind+1) - phaseDiff(ind));
                    maxT = tWindowed(ind) + frac * Ts;
                end
            end
        end

        function [minT,maxT] = extractPeakTroughEMD(obj,year,x)
            tDays = obj.Data.Time.Day;
            tDates = obj.Data.Time.Date;
            phenoYearStart = obj.Config.PhenoYearStart;
            
            maxT = nan;
            minT = nan;
            
            startDate = datetime(year,1,1) + days(phenoYearStart - 1);
            endDate = datetime(year + 1,1,1) + days(phenoYearStart - 2);

            inWindow  = tDates >= startDate & tDates < endDate;
            if sum(inWindow) < 10
                return;
            end
            xWindowed = x(inWindow);
            tWindowed = tDays(inWindow);
            tDatesWindowed = tDates(inWindow);
            
            [~,argMax] = max(xWindowed);
            maxT = tWindowed(argMax);
            
            dormancyStart = datetime(year + 1,1,1);
            dormancyEnd = datetime(year + 1,3,1);
            inDormancy = tDatesWindowed >= dormancyStart & tDatesWindowed <= dormancyEnd;
            if sum(inDormancy) >= 3
                xDormancy = xWindowed(inDormancy);
                tDormancy = tWindowed(inDormancy);

                [~,argMin] = min(xDormancy);
                minT = tDormancy(argMin);
            else
                [~,argMin] = min(xWindowed);
                minT = tWindowed(argMin);
            end
        end

        function makePlots(obj)
            tYear = obj.Data.Time.Year;
            years = obj.Metadata.Years;
            
            % --- Time-Frequency Domain Signals ---
            pm = PlotManager();
            pm.createFigure('size',[3,1],'hold','on','font',obj.DEF_FIGURE_FONT_NAME);
            pm.selectAxis(1);
            pm.plot(tYear,obj.Analysis.DWT.AnnualSignal,'k');
            pm.xlim([min(tYear),max(tYear)]);
            pm.xlabel('(a)');
            pm.title('Method 1');
            pm.selectAxis(2);
            pm.plot(tYear,real(obj.Analysis.CWT.AnnualSignal),'k');
            pm.yyaxis('right');
            pm.plot(tYear,obj.Analysis.CWT.AnnualPhase,'k--');
            pm.xlim([min(tYear),max(tYear)]);
            pm.xlabel('(b)');
            pm.title('Method 2/Method 3');
            pm.selectAxis(3);
            pm.plot(tYear,obj.Analysis.EMD.AnnualSignal,'k');
            pm.xlim([min(tYear),max(tYear)]);
            pm.xlabel('(c)');
            pm.title('Method 4');
            pm.format('IgnoreLineStyles',true);
            pm.save(fullfile(obj.SavePath,'tf_domain_signals.png'));

            % --- Peak/Dormancy ---
            pm = PlotManager();
            pm.createFigure('size',[2,1],'hold','on','font',obj.DEF_FIGURE_FONT_NAME);
            pm.selectAxis(1);
            pm.plot(years,arrayfun(@(x) obj.toDOY(x.Peak),[obj.Metrics.Method1]),'o-');
            pm.plot(years,arrayfun(@(x) obj.toDOY(x.Peak),[obj.Metrics.Method2]),'s--');
            pm.plot(years,arrayfun(@(x) obj.toDOY(x.Peak),[obj.Metrics.Method3]),'d:');
            pm.plot(years,arrayfun(@(x) obj.toDOY(x.Peak),[obj.Metrics.Method4]),'^-.');
            pm.xlim([min(years),max(years)]);
            pm.ylim([1 365]);
            pm.xlabel('(a)');
            pm.ylabel('DOY');
            pm.title('Peak');
            pm.legend({'Method 1','Method 2','Method 3','Method 4'},'Location','eastoutside');
            pm.selectAxis(2);
            pm.plot(years,arrayfun(@(x) obj.toDOY(x.Dormancy),[obj.Metrics.Method1]),'o-');
            pm.plot(years,arrayfun(@(x) obj.toDOY(x.Dormancy),[obj.Metrics.Method2]),'s--');
            pm.plot(years,arrayfun(@(x) obj.toDOY(x.Dormancy),[obj.Metrics.Method3]),'d:');
            pm.plot(years,arrayfun(@(x) obj.toDOY(x.Dormancy),[obj.Metrics.Method4]),'^-.');
            pm.xlim([min(years),max(years)]);
            pm.ylim([1 365]);
            pm.xlabel('(b)');
            pm.ylabel('DOY');
            pm.title('Dormancy');
            pm.legend({'Method 1','Method 2','Method 3','Method 4'},'Location','eastoutside');
            pm.format();
            pm.save(fullfile(obj.SavePath,'tf_peak_dormancy.png'));

            % --- Full Suite ---
            obj.makePlotFullSuite(1);
            obj.makePlotFullSuite(2);
            obj.makePlotFullSuite(3);
            obj.makePlotFullSuite(4);

            % --- Method Comparison ---
            pairs = nchoosek(1:4,2);
            for ii = 1:size(pairs,1)
                obj.makePlotMethodComparison(pairs(ii,1),pairs(ii,2));
            end
        end

        function makePlotFullSuite(obj,method)
            years = obj.Metadata.Years;
            
            pm = PlotManager();
            pm.createFigure('size',[8,1],'hold','on','font',obj.DEF_FIGURE_FONT_NAME);

            metrics = [obj.Metrics.(sprintf('Method%d',method))];
            fields = fieldnames(metrics);
            for ii = 1:length(fields)
                fieldName = strip(regexprep(fields{ii},'([A-Z])',' $1'));
                if strcmp(fieldName,'Num Cycles')
                    transformFunc = @(x) x;
                else
                    transformFunc = @(x) obj.toDOY(x);
                end
                
                pm.selectAxis(ii);
                pm.plot(years,arrayfun(@(x) transformFunc(x.(fields{ii})),metrics),'ko-');
                pm.xlim([min(years),max(years)]);
                if strcmp(fieldName,'Num Cycles')
                    pm.ylim([0,5]);
                else
                    pm.ylim([1 365]);
                end
                pm.ylabel('DOY');
                pm.title(replace(fieldName,'Num Cycles','No. Cycles'));
            end
            pm.xlabel('Year');
            pm.sgtitle(sprintf('Method % d',method));
            pm.save(fullfile(obj.SavePath,sprintf('tf_full_suite_method_%d.png',method)));
        end

        function makePlotMethodComparison(obj,ii,jj)
            metrics = fieldnames([obj.Metrics.Method1]);
            numMetrics = length(metrics);

            metricSet1 = [obj.Metrics.(sprintf('Method%d',ii))];
            metricSet2 = [obj.Metrics.(sprintf('Method%d',jj))];

            pm = PlotManager();
            pm.createFigure('size',[3,4],'hold','on','font',obj.DEF_FIGURE_FONT_NAME);
            for kk = 1:numMetrics
                fieldName = strip(regexprep(metrics{kk},'([A-Z])',' $1'));
                if strcmp(fieldName,'Num Cycles')
                    transformFunc = @(x) x;
                else
                    transformFunc = @(x) obj.toDOY(x);
                end
                
                pm.selectAxis(kk);
                x = arrayfun(@(x) transformFunc(x.(metrics{kk})),metricSet1);
                y = arrayfun(@(x) transformFunc(x.(metrics{kk})),metricSet2);
                pm.scatter(x,y,10,'k','filled');
                if strcmp(fieldName,'Num Cycles')
                    pm.plot([0,5],[0,5],'k--');
                    pm.xlim([0,5]);
                    pm.ylim([0,5]);
                else
                    pm.plot([1,365],[1,365],'k--');
                    pm.xlim([1 365]);
                    pm.ylim([1 365]);
                end
                pm.title(replace(fieldName,'Num Cycles','No. Cycles'));
                pm.pbaspect([1,1,1]);
            end
            pm.sgtitle(sprintf('Method %d vs. Method %d',ii,jj));
            pm.save(fullfile(obj.SavePath,sprintf('tf_method_comparison_%d_vs_%d.png',ii,jj)));
        end

        function makeStats(obj)
            pairs = nchoosek(1:4,2);
            for ii = 1:size(pairs,1)
                obj.makeStatsMethodComparison(pairs(ii,1),pairs(ii,2));
            end
        end

        function makeStatsMethodComparison(obj,ii,jj)
            metrics = fieldnames([obj.Metrics.Method1]);
            numMetrics = length(metrics);

            metricSet1 = [obj.Metrics.(sprintf('Method%d',ii))];
            metricSet2 = [obj.Metrics.(sprintf('Method%d',jj))];
            
            stats = nan(numMetrics,9);
            for kk = 1:numMetrics
                fieldName = strip(regexprep(metrics{kk},'([A-Z])',' $1'));
                if strcmp(fieldName,'Num Cycles')
                    transformFunc = @(x) x;
                else
                    transformFunc = @(x) obj.toDOY(x);
                end
                
                x = arrayfun(@(x) transformFunc(x.(metrics{kk})),metricSet1);
                y = arrayfun(@(x) transformFunc(x.(metrics{kk})),metricSet2);

                validInd = ~isnan(x) & ~isnan(y);
                x = x(validInd);
                y = y(validInd);
                
                e = x - y;
                straddle = abs(e) > 182;
                y(straddle & e > 0) = y(straddle & e > 0) + 365;
                y(straddle & e < 0) = y(straddle & e < 0) - 365;
                e = x - y;
                
                meanBias = mean(e);
                mae = mean(abs(e));
                rmse = sqrt((1 / length(x)) * sum(e.^2));
                [rhoc,rho,cb] = ccc(x,y);

                stats(kk,:) = [ii,jj,kk,meanBias,mae,rmse,rho,cb,rhoc];
            end
            stats = array2table(stats,'VariableNames',{'Method A','Method B','Metric','B','MAE','RMSE','rho','cb','rhoc'});
            obj.Stats = vertcat(obj.Stats,stats);
        end
    end

    methods (Static)
        function tCross = thresholdCross(x,t,tau,direction)
            tCross = nan;

            if strcmp(direction,'rising')
                ind = find(x >= tau,1,'first');
            else
                ind = find(x <= tau,1,'first');
            end

            if isempty(ind) || ind == 1
                return;
            end

            x1 = x(ind - 1);
            x2 = x(ind);
            t1 = t(ind - 1);
            t2 = t(ind);
            if abs(x2 - x1) < 1e-10
                tCross = t1;
                return;
            end

            tCross = t1 + (tau - x1) / (x2 - x1) * (t2 - t1);
        end
        
        function doy = toDOY(tDays)
            doy = nan(size(tDays));
            for ii = 1:numel(tDays)
                if ~isnan(tDays(ii))
                    doy(ii) = day(datetime(1970,1,1) + days(tDays(ii)),'dayofyear');
                end
            end
        end
    end
end
