function [tYears,V,D4,A3] = analyzeDWT(dataFile,fontName)
    arguments
        dataFile
        fontName = 'TeX Gyre Heros';
    end

    clc; close all;
    includePackage('math','graphics');

    [filepath,name] = fileparts(dataFile);
    savepath = fullfile(filepath,name);
    if ~isfolder(savepath)
        mkdir(savepath);
    end
    
    % --- Signal ---
    S = load(dataFile);

    t = double(S.t);
    x = S.x;
    L = double(S.L);

    tDate = datetime(1970,1,1) + days(t);
    tYears = year(tDate) + (day(tDate,'dayofyear') - 1) ./ 365;
    
    pm = PlotManager();
    pm.createFigure('size',[2,1],'font',fontName);
    pm.plot(tYears,x);
    pm.xlim([min(tYears),max(tYears)]);
    pm.xlabel('t (years)');
    pm.ylabel('x(t)');
    pm.format();
    pm.save(fullfile(savepath,'dwt_signal.png'));
    
    % --- Analysis ---
    filter = 'dmey';
    N = floor(log2(L)); % Maximum number of decomposition levels
    
    % Store approximation and detailed coefficients
    [c,l] = wavedec(x,N,filter);
    ca = cell(1,N);
    cd = cell(1,N);
    for k = N:-1:1
        ca{N - k + 1} = appcoef(c,l,filter,k);
        cd{N - k + 1} = detcoef(c,l,k);
    end

    caMap = zeros(N,L);
    for ii = 1:N
        coeff = abs(ca{ii});
        n = length(coeff);
        ind = max(1,floor((0:L-1) * n / L) + 1);
        caMap(ii,:) = coeff(ind);
    end

    pm = PlotManager();
    pm.createFigure('box','on','font',fontName);
    pm.imagesc(caMap);
    pm.colormap(plasma(256));
    pm.colorbar('Label','Magnitude');
    pm.yticks(1:N);
    pm.yticklabels(arrayfun(@(k) sprintf('A_{%d}',k-1),1:N,'UniformOutput',false));
    pm.xlabel('n');
    pm.title('DWT Energy Spectrum (Approximation Coefficients)');
    pm.format();
    pm.save(fullfile(savepath,'dwt_approximation_coefficients.png'));

    cdMap = zeros(N,L);
    for ii = 1:N
        coeff = abs(cd{ii});
        n = length(coeff);
        ind = max(1,floor((0:L-1) * n / L) + 1);
        cdMap(ii,:) = coeff(ind);
    end

    pm = PlotManager();
    pm.createFigure('box','on','font',fontName);
    pm.imagesc(cdMap);
    pm.colormap(plasma(256));
    pm.colorbar('Label','Magnitude');
    pm.yticks(1:N);
    pm.yticklabels(arrayfun(@(k) sprintf('D_{%d}',k-1),1:N,'UniformOutput',false));
    pm.xlabel('n');
    pm.title('DWT Energy Spectrum (Detailed Coefficients)');
    pm.format();
    pm.save(fullfile(savepath,'dwt_detailed_coefficients.png'));
    
    % Compute coefficient energies
    caEnergy = zeros(1,N);
    cdEnergy = zeros(1,N);
    for k = 1:N
        caEnergy(k) = sum(ca{k}.^2);
        cdEnergy(k) = sum(cd{k}.^2);
    end

    pm = PlotManager();
    pm.createFigure('size',[3,1],'font',fontName);
    pm.selectAxis(1);
    pm.plot(0:(N - 1),db(caEnergy),'o-');
    pm.xlabel('j');
    pm.ylabel('Energy (dB)');
    pm.title('Approximation Coefficients');
    pm.selectAxis(2);
    pm.plot(0:(N - 1),db(cdEnergy),'o-');
    pm.xlabel('j');
    pm.ylabel('Energy (dB)');
    pm.title('Detailed Coefficients');
    pm.format();
    pm.save(fullfile(savepath,'dwt_energy.png'));
    
    % Reconstruction
    pm = PlotManager();
    pm.createFigure('size',[N,1]);
    for ii = 1:N
        pm.selectAxis(ii);
        y = wrcoef('a',c,l,filter,N - ii + 1);
        pm.plot(tYears,y,'k');
        pm.xlim([min(tYears),max(tYears)]);
        pm.ylabel(sprintf('c_{%d}(t)',ii - 1));
    end
    pm.xlabel('t (years)');
    pm.sgtitle('Approximation Reconstruction');
    pm.save(fullfile(savepath,'dwt_approximation_reconstruction.png'));
    
    pm = PlotManager();
    pm.createFigure('size',[N,1]);
    for ii = 1:N
        pm.selectAxis(ii);
        y = wrcoef('d',c,l,filter,N - ii + 1);
        pm.plot(tYears,y,'k');
        pm.xlim([min(tYears),max(tYears)]);
        pm.ylabel(sprintf('w_{%d}(t)',ii - 1));
    end
    pm.xlabel('t (years)');
    pm.sgtitle('Detailed Reconstruction');
    pm.save(fullfile(savepath,'dwt_detailed_reconstruction.png'));

    % Output components
    annualLevel = 4;
    V = 0;
    for ii = annualLevel:(N - 2)
        V = V + wrcoef('d',c,l,filter,N - ii);
    end
    D4 = wrcoef('d',c,l,filter,N - annualLevel);
    A3 = wrcoef('a',c,l,filter,N - annualLevel + 1);

    pm = PlotManager();
    pm.createFigure('size',[3,1],'hold','on','font',fontName);
    pm.selectAxis(1);
    pm.plot(tYears,V,'k');
    pm.plot(tYears,x,'k--');
    pm.xlim([min(tYears),max(tYears)]);
    pm.ylabel('V(t)');
    pm.title('Total Intra-annual Variability');
    pm.selectAxis(2);
    pm.plot(tYears,D4,'k');
    pm.plot(tYears,x,'k--');
    pm.xlim([min(tYears),max(tYears)]);
    pm.ylabel('w_4(t)');
    pm.title('Semi-annual Variability');
    pm.selectAxis(3);
    pm.plot(tYears,A3,'k');
    pm.plot(tYears,x,'k--');
    pm.xlim([min(tYears),max(tYears)]);
    pm.ylabel('c_3(t)');
    pm.title('Inter-annual Trends');
    pm.save(fullfile(savepath,'dwt_output_components.png'));
end
